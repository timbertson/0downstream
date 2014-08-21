import os
import re

import json
import logging
import hashlib
import subprocess

from version import Version, VersionComponent

from .common import cached_property, Implementation, BaseProject, BaseRelease, getjson, get
from .. import composite_version
from ..archive import Archive
from ..tag import Tag

logger = logging.getLogger(__name__)

class FileEntry(object):
	def __init__(self, repo, fields):
		self.repo = repo
		self.path, self.md5_digest, _mode = fields
		self.parts = self.path.strip('/').split('/')
		self.kind = [0]

	@property
	def url(self):
		return self.repo.root + self.path

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

detect_opam_metadata = os.path.join(
	os.path.dirname(__file__), '..', '..', 'tools', 'detect-opam-metadata.xml'
)

class Release(BaseRelease):
	def __init__(self, project, version):
		super(Release, self).__init__()
		self.project = project
		self.version = version
		self.id = project.id + '.' + version.upstream

		self._url_path = ['packages', self.project.id, self.id]
		self.runtime_dependencies = [] #XXX
	
	@property
	def url(self):
		info = self.release_info
		print(repr(info['url']))
		return info['url']['url']

	@property
	def info_page(self):
		return self.project.repo.root + '/'.join(self._url_path) + '/'
	
	@cached_property
	def release_info(self):
		rv = {}
		for kind in ('opam', 'descr', 'url'):
			rv[kind] = self._metadata(kind)
		return rv

	def _metadata(self, kind):
		meta_files = list(self.project.repo.files_at(*(self._url_path + [kind])))
		if not meta_files:
			logger.warn("No %s file found for %s" % (kind, self.id))
			return None
		assert len(meta_files) == 1, "%s %s files found for %s" % (len(meta_files), kind, self.id)
		content = meta_files[0].contents()
		# print(repr(content))
		cmd = [ '0install', 'run', detect_opam_metadata, '--type', kind ]
		logger.debug("Running: %r" % (cmd,))
		proc = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout=subprocess.PIPE)
		out, _err = proc.communicate(content)
		if proc.poll() != 0:
			raise RuntimeError("Failed command: %r" % (cmd,))
		# print('GOT: ' + repr(out))
		return json.loads(out)
	
	# @property
	# def dependency_names(self):
	# 	get = lambda dep: dep.upstream_id
	# 	return set(map(get, self.runtime_dependencies)).union(map(get, self.compile_dependencies))
	#
	# @cached_property
	# def release_info(self):
	# 	root = os.listdir(self.archive.local)[0]
	# 	with open(os.path.join(self.archive.local, root, 'package.json')) as json_file:
	# 		return json.load(json_file)
	
	def copy(self):
		return type(self)(project=self.project, version=self.version)

	# def detect_dependencies(self, resolver):
	# 	self.runtime_dependencies = []
	# 	self.compile_dependencies = []
	# 	def add_dependency(tagname, name, version_spec, attrs=None, dest=None):
	# 		location = resolver(Npm(name))
	# 		if location is None:
	# 			logger.info("Skipping dependency: %s" % (name,))
	# 			return

	# 		url = location.url
	# 		tag = Tag(tagname, {'interface': url})
	# 		if location.command is not None:
	# 			tag.attr('command', location.command)
	# 		tag.upstream_id = name
	# 		if attrs is not None:
	# 			for k,v in attrs.items():
	# 				tag.attr(k, v)

	# 		version = _parse_version_info(version_spec)
	# 		if version:
	# 			tag.children.append(version)
	# 		if dest is None:
	# 			self.runtime_dependencies.append(tag)
	# 			self.compile_dependencies.append(tag)
	# 		else:
	# 			dest.append(tag)

	# 	package_info = self.release_info
	# 	for (name, version_spec) in package_info.get('dependencies', {}).items():
	# 		add_dependency('requires', name, version_spec)

	# 	# for (name, version_spec) in package_info.get('optionalDependencies', {}).items():
	# 	# 	add_dependency('requires', name, version_spec, {'importance': 'recommended'})

	# 	for (name, version_spec) in package_info.get('peerDependencies', {}).items():
	# 		add_dependency('restricts', name, version_spec)

	# 	for (name, version_spec) in package_info.get('devDependencies', {}).items():
	# 		add_dependency('requires', name, version_spec, dest=self.compile_dependencies)

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

