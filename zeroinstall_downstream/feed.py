from .project import SOURCES, make
from .archive import Archive
from xml.dom import minidom
from version import Version
import subprocess
import logging

log = logging.getLogger(__name__)

ZI = "http://zero-install.sourceforge.net/2004/injector/interface"
GFXMONK = "http://gfxmonk.net/dist/0install"
ZEROCOMPILE = "http://zero-install.sourceforge.net/2006/namespaces/0compile"

class Feed(object):
	def __init__(self, doc, uri, project=None):
		self.doc = doc
		self.uri = uri
		self.project = project
		self.interface = doc.documentElement
		self.interface.setAttribute("xmlns", ZI)
		self.interface.setAttribute("xmlns:gfxmonk", GFXMONK)
		self.interface.setAttribute("xmlns:compile", ZEROCOMPILE)

	@classmethod
	def from_project(cls, project, dest_uri):
		dom = minidom.getDOMImplementation()
		doc = dom.createDocument(ZI, "interface", None)
		feed = cls(doc, project=project, uri = dest_uri)
		feed.update_metadata()
		group = feed._mknode("group")
		feed.interface.appendChild(group)
		return feed

	@classmethod
	def from_file(cls, infile):
		doc = minidom.parse(infile)
		interface = doc.documentElement
		uri = interface.getAttribute('uri')
		project_info = interface.getElementsByTagNameNS(GFXMONK, 'upstream')[0]
		project_attrs = dict([(attr.name, attr.value) for attr in project_info.attributes.values()])
		update_metadata = project_attrs.pop('update-metadata', 'true') == 'true'
		try:
			project = make(**project_attrs)
		except TypeError as e:
			raise ValueError("Can't construct project definition from attributes %r\nOriginal error: %s" % (project_attrs, e))
		feed = cls(doc, project=project, uri = uri)
		if update_metadata:
			feed.update_metadata()
		return feed

	def update_metadata(self):
		self.interface.setAttribute('uri', self.uri)
		name = self._create_or_update_child_node(self.interface, "name", self.name)
		summary = self._create_or_update_child_node(self.interface, "summary", self.project.summary)
		project_info = self._create_or_update_child_node(self.interface, "gfxmonk:upstream", ns=GFXMONK)
		project_info.setAttribute('type', self.project.upstream_type)
		project_info.setAttribute('id', self.project.upstream_id)
		publish = self._create_or_update_child_node(self.interface, "gfxmonk:publish", "third-party", ns=GFXMONK)
		homepage = self._create_or_update_child_node(self.interface, "homepage", self.project.homepage)
		description = self._create_or_update_child_node(self.interface, "description", self.project.description)

	def _create_or_update_child_node(self, elem, node_name, content=None, ns=None):
		children = elem.childNodes
		for child in children:
			if child.nodeType == child.ELEMENT_NODE and child.tagName == node_name:
				log.debug("using existing node %s for node type %s" % (child, node_name))
				new_node = child
				while new_node.hasChildNodes():
					_del = new_node.removeChild(new_node.childNodes[0])
					_del.unlink()
				break
		else:
			new_node = self._mknode(node_name)
			if elem.hasChildNodes() and elem.getElementsByTagName('group'):
				first_group = elem.getElementsByTagName('group')[0]
				elem.insertBefore(new_node, first_group)
			else:
				elem.appendChild(new_node)
		if content is not None:
			log.debug("setting %s to %s" %(node_name, content))
			content = self.doc.createTextNode(content)
			new_node.appendChild(content)
		return new_node

	def _mknode(self, node_name, content=None, ns=None):
		if ns is None:
			node = self.doc.createElement(node_name)
		else:
			node = self.doc.createElementNS(ns, node_name)
		if content is not None:
			content = self.doc.createTextNode(content)
			node.appendChild(content)
		return node

	@property
	def name(self):
		assert '/' in self.uri, "Bad URI: %s" % (self.uri,)
		return self.uri.rstrip('/').rsplit('/', 1)[1].rsplit('.', 1)[0]

	def add_latest_implementation(self, extract=None):
		assert self.has_new_implementations, "feed already up to date"
		release = self.project.latest_release
		group = self.interface.getElementsByTagName("group")[-1]
		impl = self._mknode('implementation')
		impl.setAttribute('version', release.version)
		impl.setAttribute('released', release.released)

		# release has a default `extract
		extract = extract or release.extract
		archive = Archive(release.url, type=release.archive_type, extract=extract)
		# Archive may guess an `extract` value, if there was only one toplevel
		# specified and we didn't pass an extract explicitly
		extract = archive.extract

		archive_tag = self._mknode('archive')
		def set_archive_attr(attr, val):
			log.debug("setting archive %s to %r" %(attr, val))
			archive_tag.setAttribute(attr, val)

		set_archive_attr('href', release.url)
		if extract is not None:
			set_archive_attr('extract', extract)
		if archive.type is not None:
			set_archive_attr('type', archive.type)
		set_archive_attr('size', str(archive.size))
		impl.appendChild(archive_tag)

		manifest_tag = self._mknode('manifest-digest')
		manifest_tag.setAttribute('sha256', archive.manifests['sha256'])
		impl.appendChild(manifest_tag)

		impl.setAttribute('id', "sha1new=%s" % (archive.manifests['sha1new']))
		group.appendChild(impl)
	
	@property
	def has_new_implementations(self):
		versions = self.interface.getElementsByTagName("implementation")
		versions = map(lambda x: x.getAttribute("version"), versions)
		versions = map(Version.parse, versions)
		versions = list(versions)
		if not versions:
			log.debug("no existing versions")
			return True
		last_version = max(versions)
		project_version = Version.parse(self.project.latest_version)

		log.debug("comparing last feed version (%s) to latest (%s)" % (
			last_version, project_version))
		if project_version == last_version:
			return False

		if project_version < last_version:
			raise ValueError("project version (%s) is OLDER than latest version in feed! (%s)" % (
				project_version, last_version))

		return True

	@property
	def xml(self):
		xml = self.doc.toxml()
		proc = subprocess.Popen(['xmlformat'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		stdout, _ = proc.communicate(xml)
		assert proc.returncode == 0, "xmlformat failed!"
		return stdout

	def save(self, outfile):
		outfile.write(self.xml)

