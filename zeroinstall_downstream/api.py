import os
import errno
import tempfile
import logging
import subprocess
from xml.dom import XMLNS_NAMESPACE
COMPILE_NAMESPACE='http://zero-install.sourceforge.net/2006/namespaces/0compile'

logger = logging.getLogger(__name__)

from .tag import Tag, Attribute
from .feed import Feed

_default_template = '''
<?xml version="1.0"?>
<?xml-stylesheet type='text/xsl' href='interface.xsl'?>
<interface xmlns="http://zero-install.sourceforge.net/2004/injector/interface">
	<implementation version="{version}">
	</implementation>
</interface>
'''.strip()

def _ensureNamespace(doc, prefix, url):
	root = doc.documentElement
	if not root.getAttributeNS(XMLNS_NAMESPACE, prefix):
		root.setAttributeNS(XMLNS_NAMESPACE, 'xmlns:' + prefix, url)

class _CompileProperties(object):
	def __init__(self, command, children):
		self.command = command
		self.children = children
	
	def addTo(self, impl, doc, template):
		_ensureNamespace(doc, 'compile', COMPILE_NAMESPACE)
		for child in self.children:
			child.addTo(impl, doc)

		command = self.command.addTo(impl, doc)
		command.appendChild(template)

class Release(object):
	'''
	This class wraps an internal project / release / feed
	with all the API methods expected by config scripts.

	This class should expose no unnecessary internal details,
	and maintain backwards compatibility where possible.
	'''
	def __init__(self, project, release, location, opts):
		self._project = project
		self._release = release
		self._location = location
		self.upstream_type = project.upstream_type
		self.id = project.id
		self.template = None
		self.version = release.version.derived
		self.template_vars = {
			'version': release.version.derived
		}
		self._compile_properties = None
		self.implementation_children = []
		self._local_feeds = []
		self._opts = opts
		self._location_resolver = self._opts.config.resolve_project
		self._peers = []
	
	@property
	def requires_compilation(self):
		return self._compile_properties is not None
	
	def set_compile_properties(self,
		command=None,
		dup_src=False,
	):
		assert command is not None, "command required"
		children = []

		if dup_src:
			children.append(Attribute('compile:dup-src', 'true', namespace=COMPILE_NAMESPACE))

		self._compile_properties = _CompileProperties(command, children)
	
	def rename(self, *a):
		return self._release.archive.rename(*a)
	
	def add_to_impl(self, tag):
		self.implementation_children.append(tag)

	def ensure_template(self):
		if self.template is None:
			self.template = _default_template

	def guess_dependencies(self, *a):
		self._release.detect_dependencies(self._location_resolver, *a)
	
	def set_implementation_id(self, id):
		self.interface_children.push(Attribute('id', id))
	
	def create_dependencies(self):
		from . import actions
		deps = self._release.compile_dependencies if self.requires_compilation else self._release.runtime_dependencies

		for dep in deps:
			url = dep['interface']

			if dep.get('importance') == 'recommended':
				logger.info("skipping optional dependency: %s" % (url,))
				continue

			project_id = None
			# see if it's an existing feed
			local_path = self._local_feed_for(url)
			if local_path:
				attrs = Feed.from_path(local_path).get_upstream_attrs()
				project_id = attrs.get('id', None)

			if project_id is None:
				# not yet found. Try scanning all named dependencies
				# and see if we get one that _would_ generate the given url
				for dep in sorted(self._release.dependency_names):
					p = type(self._project)(dep)
					loc = self._location_resolver(p)
					if loc and loc.url == url:
						# found a match!
						project_id = dep
						break

			if project_id is None:
				logger.info("skipping external dependency: %s" % (url,))
				continue

			project = type(self._project)(project_id)
			location = self._location_resolver(project)
			if location is None or location.path is None:
				logger.info("Ignoring dependency %s" % (project_id,))
				continue

			if os.path.exists(location.path):
				if self._opts.recursive:
					self._opts.recursive(project, location, version=None, opts=self._opts)
				else:
					logger.debug("Skipping existing dependency %s (use --recursive to update dependencies)" % project_id)
			else:
				# TODO: create a version which will satisfy the dependency
				(self._opts.recursive or actions.create)(project, location, None, self._opts)
	
	@property
	def release_info(self):
		return self._release.release_info
	
	def __enter__(self):
		self._release.__enter__()

	def __exit__(self, *a):
		for feed in self._local_feeds:
			try:
				os.remove(feed)
			except OSError as e:
				if e.errno == errno.ENOENT:
					continue
				raise
			logger.debug("cleaned up local feed %s", feed)
		self._release.__exit__(*a)

	def _local_feed_for(self, url):
		path = self._opts.config.local_path_for(url)
		if path is not None:
			if os.path.exists(path):
				return path
			else:
				logging.debug("Non-existant local feed %s" % (path,))

	def _add_implementation(self, feed):
		pass

	def fork(self):
		'''Clones this release and returns the new object
		When this (main) feed is generated, any forked implementations
		will also be added to the result'''
		impl = type(self)(project=self._project, release=self._release, location=self._location, opts=self._opts)
		impl.template = self.template
		impl.template_vars = self.template_vars.copy()
		self._peers.append(impl)

	def _generate_feed(self, local):
		self.ensure_template()
		with tempfile.NamedTemporaryFile(prefix="0downstream-", suffix="-%s.xml" % self._project.id, delete=False) as dest:
			self._local_feeds.append(dest.name)

			dest.write(self.template)
			dest.seek(0)

			feed = Feed(dest)
			feed.update_metadata(self._project, self._location)
			impl = feed.create_or_update_child_node(feed.interface, 'implementation')
			for tag in self.implementation_children:
				tag.addTo(impl, feed.doc)

			for dep in self._release.runtime_dependencies:
				dep.addTo(impl, feed.doc)

			if self.requires_compilation:
				# create compile:impl and reparent all of impl's children into that:
				_ensureNamespace(feed.doc, 'compile', COMPILE_NAMESPACE)

				impl_template = feed.doc.createElementNS(COMPILE_NAMESPACE, 'compile:implementation')
				for child in list(impl.childNodes)[:]:
					impl.removeChild(child)
					impl_template.appendChild(child)

				impl.setAttribute("arch", "*-src")
				for dep in self._release.compile_dependencies:
					dep.addTo(impl, feed.doc)

				self._compile_properties.addTo(impl, feed.doc, impl_template)

			self._release.archive.add_to(impl, feed.doc)
			if not impl.hasAttribute('id'):
				impl.setAttribute('id', self._release.archive.id)

			feed.save(dest)
			dest.seek(0)

			from . import template_expand as expand
			expand.process_doc(feed.doc, self.template_vars)

			feed.save(dest)
			dest.seek(0)
			logging.debug("local feed XML: %s" % feed.xml)

			if not local:
				# include feed peers, by simply calling this method on them and
				# then including them using 0publish.
				#
				# There are surely quicker ways, but they're a little awkward to code.
				for peer in self._peers:
					peer_feed = peer._generate_feed(local=local)
					subprocess.check_call(['0publish', '--add-from', peer_feed])

			return dest.name

	@property
	def working_copy(self):
		local = self._release.archive.local
		extract = self._release.archive.extract
		return local if extract is None else os.path.join(local,extract)

	def generate_local_feed(self):
		return self._generate_feed(local=True)

	def generate_feed(self):
		return self._generate_feed(local=False)

class FeedLocation(object):
	def __init__(self, url, path=None, command=None):
		self.url = url
		self.path = path
		self.command = command

	def _key(self): return (self.url, self.path, self.command)
	def __eq__(self, other): return type(other) == type(self) and self._key() == other._key()
	def __ne__(self, other): return not self.__eq__(other)
	def __hash__(self): return hash(self._key())
	def __repr__(self): return "<FeedLocation %r>" % (self._key(),)

