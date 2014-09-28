import os
import re

import json
import logging
import hashlib
import subprocess
import tarfile

from version import Version, VersionComponent

from .common import cached_property, Implementation, BaseProject, BaseRelease, getjson, get
from .. import composite_version
from ..archive import Archive
from ..tag import Tag

logger = logging.getLogger(__name__)

class FakeFileEntry(object):
	def __init__(self, url, contents):
		self.url = url
		self.contents = contents

class FileEntry(object):
	def __init__(self, repo, fields):
		self.repo = repo
		self.path, self.md5_digest, _mode = fields
		self.parts = self.path.strip('/').split('/')
		self.kind = [0]

	@property
	def url(self):
		return self.repo.root + self.path

	@cached_property
	def contents(self):
		url = self.url
		c = get(url)
		md5 = hashlib.md5(c).hexdigest()
		assert md5 == self.md5_digest, "Digest error for %s\nExpected %s, got %s" % (url, self.md5_digest, md5)
		return c

class Repo(object):
	def __init__(self, root):
		assert root.endswith('/'), "repo root must end with a slash"
		self.root = root
	
	@cached_property
	def file_list(self):
		fields = [line.split() for line in get(self.root + "urls.txt").splitlines()]
		return [FileEntry(self, fields) for fields in fields]

	def files_at(self, *parts):
		parts = list(parts)
		l = len(parts)
		common_prefix = lambda file: file.parts[:l] == parts
		return filter(common_prefix, self.file_list)

	def package_names(self):
		return set([f.parts[1] for f in self.files_at('packages')])

	def package_versions(self, name):
		full_versions = [f.parts[2] for f in self.files_at('packages',name)]
		def remove_leading(str, prefix):
			assert str.startswith(prefix), "Expected %s to start with %s" % (str, prefix)
			return str[len(prefix):]

		version_strings = map(lambda s: remove_leading(s, name + "."), full_versions)
		return filter(None, map(composite_version.try_parse, version_strings))

opam_helper = os.path.join(
	os.path.dirname(__file__), '..', '..', 'tools', 'opam-0downstream-helper', 'run.xml'
)

class Release(BaseRelease):
	def __init__(self, project, version):
		super(Release, self).__init__()
		self.project = project
		self.version = version
		self.id = project.id + '.' + version.upstream

		self._url_path = ['packages', self.project.id, self.id]

		self.runtime_dependencies = []
		self.compile_dependencies = []
	
	def _enter_archive(self):
		archive = super(Release, self)._enter_archive(extract=None)
		return archive

	@property
	def url(self):
		info = self.release_info
		# print(repr(info['url']))
		urlinfo = info['url']
		if urlinfo is None:
			from zeroinstall_downstream import main
			config = main._load_config()
			urlinfo = {
				'kind': 'http',
				'url': config.empty_archive_url,
			}
		urlkind = urlinfo['kind']
		assert urlkind in (None, 'http'), "Unsupported URL kind: %s" % (urlkind,)
		return urlinfo['url']

	@property
	def info_page(self):
		return self.project.repo.root + '/'.join(self._url_path) + '/'

	def add_opam_files(self, prefix, src_path, base):
		base_path, base_url = base
		archive_name = self.id + ".tar.gz"
		archive_path = os.path.join(base_path, archive_name)
		archive_url = base_url + '/' + archive_name
		if not os.path.exists(base_path):
			os.makedirs(base_path)

		# opam repos change opam files whenever they like, so
		# we need to mirror them on feed creation

		with tarfile.open(archive_path, 'w:gz') as archive:
			try:
				def add_file(relative_path, contents):
					from StringIO import StringIO
					filecontents = StringIO(contents)

					info = tarfile.TarInfo(name = "%s/%s/%s" % (prefix, self.id, relative_path))
					info.size=len(filecontents.buf)
					archive.addfile(tarinfo=info, fileobj=filecontents)

				for file in self.project.repo.files_at(*self._url_path):
					relative_path = os.path.join(*file.parts[len(self._url_path):])

					if relative_path == 'url':
						continue

					add_file(relative_path, get(file.url))

				# Add a "src" file, which is read/understood by opam-src-build.
				# This is very hacky, but prevents an entire compile step just to get
				# around a hard-coded path
				if src_path is not None:
					with open(src_path) as src_file:
						add_file('src', src_file.read())

			except Exception as e:
				os.remove(archive_path)
				raise e

		self.archive.add_archive(
			source=archive_url,
			local_file = archive_path,
		)

	
	@cached_property
	def release_info(self):
		rv = {}
		for kind in ('opam', 'descr', 'url'):
			rv[kind] = self._metadata(kind)
		logger.debug("Release info for %s: %r" % (self.id, rv))
		return rv

	def _metadata(self, kind):
		meta_files = list(self.project.repo.files_at(*(self._url_path + [kind])))
		if not meta_files:
			logger.warn("No %s file found for %s" % (kind, self.id))
			return None
		assert len(meta_files) == 1, "%s %s files found for %s" % (len(meta_files), kind, self.id)
		content = meta_files[0].contents
		# print(repr(content))
		cmd = [ '0install', 'run', '--command', 'to-json', opam_helper, '--type', kind ]
		logger.debug("Running: %r" % (cmd,))
		proc = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout=subprocess.PIPE)
		out, _err = proc.communicate(content)
		if proc.poll() != 0:
			raise RuntimeError("Failed command: %r" % (cmd,))
		# print('GOT: ' + repr(out))
		return json.loads(out)
	
	def copy(self):
		return type(self)(project=self.project, version=self.version)

	def detect_dependencies(self, resolver, ocaml_feed):
		self.runtime_dependencies = []
		self.compile_dependencies = []
		self.dependency_names = set()
		def add_dependency(tagname, name, attrs=None):
			self.dependency_names.add(name)
			location = resolver(Opam(name))
			if location is None:
				logger.info("Skipping dependency: %s" % (name,))
				return

			tag = location.require_tag(tagname)
			tag.attr('arch','src')
			if attrs is not None:
				for k,v in attrs.items():
					tag.attr(k, v)

			# XXX do any opam packages have runtime dependencies?
			self.compile_dependencies.append(tag)

		# see zeroinstall_downstream/project/opam/opam_to_json.ml
		def version_visitor(attrs, invert=False):
			not_before = 'not-before'
			before = 'before'
			if invert:
				# swap the meaning of `before` and `not-before`
				# (invert means we're parsing a `conflicts`, which is implemented
				# in ZI using a <restricts> element with the negation of the conflict
				before, not_before = not_before, before

			def attr(name, val):
				assert name not in attrs, "Attribute %s set multiple times" % (name,)

			def visit_version(node):
				assert node['type'] == 'version', repr(node)
				op = node['op']
				ver = node['version']
				try:
					ver = Version.parse(ver, coerce=True)
				except StandardError as e:
					logger.debug("Couldn't parse version string: %s" % (ver,), exc_info=True)
					logger.warn("Couldn't parse version string: %s" % (ver,))
					return
				if op == "=":
					attr(not_before, ver)
					attr(before, ver.next())
				elif op == '!=':
					# XXX we should allow `before` this version as well,
					# but that'd be more awkward to implement
					attr(not_before, ver.increment())
				elif op == ">=":
					attr(not_before, ver)
				elif op == ">":
					attr(not_before, ver.increment())
				elif op == "<=":
					attr(before, ver.increment())
				elif op == "<":
					attr(before, ver)
			return visit_version

		def visit(node, delegate):
			if node is None: return

			if isinstance(node, list):
				# composite formula
				# tuple, one of:
				# && (a,b)
				# || (a,b)
				op, a, b = node
				if op == '&&':
					visit(a, delegate)
					visit(b, delegate)
				elif op == '||':
					logger.warn("Unable to process boolean OR, taking first branch only")
					visit(a, delegate)
				else:
					assert False, "Unknown op: %s" % (op,)

			elif isinstance(node, dict):
				# base-level atom, pass it to delegate
				delegate(node)
			else:
				assert False, "Unknown dependency type: %r" % (node,)

		def visit_toplevel(node, tagname, invert=False):
			def visit_dep(node):
				assert node['type'] == 'dependency'
				constraints = node['constraints']
				name = node['name']

				attrs = {}
				visit_version = version_visitor(attrs, invert=invert)
				visit(constraints, visit_version)
				if invert and not attrs:
					# if we have no constraints and invert=True, that means
					# we don't want _any_ version to be selected. So just make
					# an impossible constraint
					# NOTE: we use literal 'before' here because we don't want this to be affected by invert
					attr('before', '0-pre')

				add_dependency(tagname, name, attrs)
			visit(node, visit_dep)

		def visit_compiler_version(node):
			attrs = {}
			constraints = None
			visit_version = version_visitor(attrs)
			visit(node, visit_version)
			if attrs:
				self.compile_dependencies.add(
					Tag('requires', {'interface':ocaml_feed}, children=[
						Tag('version', attrs)
					])
				)

		package_info = self.release_info['opam']
		visit_toplevel(package_info['depends'], 'requires')
		visit_toplevel(package_info['depends_optional'], 'requires')
		visit_toplevel(package_info['conflicts'], 'restricts', invert=True)
		visit_compiler_version(package_info['ocaml_version'])

		def warn_unhandled(key):
			val = package_info[key]
			if val:
				logger.warn("Don't yet know how to handle %s: %r" % (key, val))

		# XXX handle these
		warn_unhandled('depends_external') # a set of strings

		logger.debug("After processing deps, compile_dependencies = %r" %(self.compile_dependencies,))

class Opam(BaseProject):
	upstream_type = 'opam'
	base = 'http://opam.ocaml.org/'
	repo = Repo(base)

	@cached_property
	def releases(self):
		rv = {}
		for ver in self.repo.package_versions(self.id):
			rv[ver] = Release(self, ver)
		return rv

	@classmethod
	def parse_uri(cls, uri):
		try:
			match = re.match('(opam:|[^:]+://opam.ocaml.org/packages/)(?P<id>[^/]+)', uri)
			return {
				'type': cls.upstream_type,
				'id': match.group('id')
			}
		except StandardError as e:
			logger.debug(e, exc_info=True)
			raise ValueError("can't parse opam project from %s" % (uri,))

	@property
	def summary(self):
		return self.id + " opam package"

	@property
	def description(self):
		descr = self.latest_release.release_info['descr']
		if not descr: return ""
		return descr['summary'] + '\n' + descr['description']
	
	@property
	def homepage(self):
		return self.latest_release.info_page

