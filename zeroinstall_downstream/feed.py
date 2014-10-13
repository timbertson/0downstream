import os
import subprocess
import logging
from xml.dom import minidom
from version import Version

from .project import SOURCES, make
from .archive import Archive
from .composite_version import CompositeVersion

log = logging.getLogger(__name__)

ZI = "http://zero-install.sourceforge.net/2004/injector/interface"
GFXMONK = "http://gfxmonk.net/dist/0install"
ZEROCOMPILE = "http://zero-install.sourceforge.net/2006/namespaces/0compile"

def escape_0template(s):
	return s.replace('{', '{{').replace('}', '}}')

class Feed(object):
	def __init__(self, infile):
		self.doc = minidom.parse(infile)
		self.interface = self.doc.documentElement
	
	@classmethod
	def from_path(cls, path):
		with open(path) as f:
			return cls(f)

	def update_metadata(self, project, location):
		self.interface.setAttribute("xmlns", ZI)
		self.interface.setAttribute("xmlns:gfxmonk", GFXMONK)
		self.interface.setAttribute("xmlns:compile", ZEROCOMPILE)

		feed_for = self.create_or_update_child_node(self.interface, "feed-for")
		feed_for.setAttribute("interface", location.url)

		name = os.path.splitext(os.path.basename(location.path))[0]
		self._default_child_node(self.interface, "name", name)
		self._default_child_node(self.interface, "summary", project.summary)
		self._default_child_node(self.interface, "homepage", project.homepage)
		self._default_child_node(self.interface, "description", escape_0template(project.description))

		project_info = self.create_or_update_child_node(self.interface, "gfxmonk:upstream", ns=GFXMONK)
		project_info.setAttribute('type', project.upstream_type)
		project_info.setAttribute('id', project.id)

	def make_canonical(self):
		for node in self.interface.childNodes:
			if node.nodeType == node.ELEMENT_NODE and node.localName == 'feed-for':
				break
		else:
			raise RuntimeError("no <feed-for> element found")
		url = node.getAttribute("interface")
		assert url, 'feed-for has no "interface" attribute'
		self.interface.setAttribute("uri", url)
		node.parentNode.removeChild(node)
		node.unlink()
	
	def get_upstream_attrs(self):
		attrs = {}
		for node in self.interface.childNodes:
			if node.nodeType == node.ELEMENT_NODE and node.localName == 'upstream' and node.namespaceURI == GFXMONK:
				break
		else:
			return attrs

		for idx in range(0, node.attributes.length):
			attr = node.attributes.item(idx)
			attrs[attr.localName] = attr.value
		return attrs

	def guess_project(self):
		attrs = self.get_upstream_attrs()
		return make(type=attrs['type'], id=attrs['id'])
	
	def _default_child_node(self, *a, **k):
		return self.create_or_update_child_node(*a, create_only=False, **k)

	def create_or_update_child_node(self, elem, node_name, content=None, ns=None, create_only=False):
		children = elem.childNodes
		for child in children:
			if child.nodeType == child.ELEMENT_NODE and child.tagName == node_name:
				if create_only:
					log.debug("skipping existing node %s for node type %s" % (child, node_name))
					return
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
	def published_versions(self):
		'''returns an enumeration of Version objects'''
		implementations = self.interface.getElementsByTagName("implementation")
		return sorted(set(map(lambda x: Version.parse(x.getAttribute("version")), implementations)))
	
	def unpublished_versions(self, project, newest_only=False):
		'''returns an enumeration of ComponsiteVersion objects'''
		versions = set(self.published_versions)
		log.debug("published versions: %r" % (versions,))

		if newest_only:
			project_versions = [max(project_versions)]
		else:
			project_versions = project.versions
		log.debug("project versions: %r" % (project_versions,))

		unpublished_versions = set()
		for version in project_versions:
			if version.derived not in versions:
				unpublished_versions.add(version)

		log.debug("unpublished versions: %r" % (unpublished_versions,))
		return unpublished_versions

	@property
	def xml(self):
		xml = self.doc.toxml()
		proc = subprocess.Popen(['xmlformat'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		stdout, _ = proc.communicate(xml.encode('utf-8'))
		assert proc.returncode == 0, "xmlformat failed!"
		return stdout.decode('utf-8')

	def save(self, outfile):
		outfile.seek(0)
		outfile.truncate()
		outfile.write(self.xml)

	def save_to_path(self, path):
		with open(path, 'w') as f:
			self.save(f)
