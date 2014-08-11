from __future__ import print_function
import re
import logging
import datetime
from .common import cached_property, Implementation, BaseProject, BaseRelease, getjson
from .. import composite_version
from ..archive import Archive
from ..tag import Tag

class Release(BaseRelease):
	def __init__(self, project, version, info, project_metadata):
		super(Release, self).__init__()
		self.project = project
		self.project_metadata = project_metadata
		self.version = version
		self.released = info['upload_time'][:10]
		self.info = info
		self.url = info['url']
		self.supports_python_3 = 'Programming Language :: Python :: 3' in project_metadata['info']['classifiers']
		self.runtime_dependencies = []
		#TODO: is there a separate source for these?
		self.compile_dependencies = self.runtime_dependencies
		self.dependency_names = set()
	
	def copy(self):
		return type(self)(project=self.project, version=self.version, info=self.info, project_metadata=self.project_metadata)
	
	def detect_dependencies(self, resolver, metadata):
		logging.debug("extract_depependencies: pypi petadata = %r", metadata)
		for requirement in metadata['install_requires']:
			if not re.match('^[-_a-zA-Z.]+$', requirement):
				raise RuntimeError("Can't yet process pypi version restrictions: %s" % requirement)

			name = requirement
			self.dependency_names.add(name)

			location = resolver(Pypi(name))
			if location is None:
				logging.info("Skipping dependency: %s" % (name,))
				return

			url = location.url
			tag = Tag('requires', {'interface': url})
			if location.command is not None:
				tag.attr('command', location.command)
			self.runtime_dependencies.append(tag)


class Pypi(BaseProject):
	upstream_type = 'pypi'
	def __init__(self, id):
		self.id = id
		self.upstream_id = id

	@cached_property
	def _info(self):
		return getjson('https://pypi.python.org/pypi/' + self.id + '/json')

	@property
	def url(self):
		return "http://pypi.python.org/pypi/" + self.id
	
	@classmethod
	def parse_uri(cls, uri):
		try:
			match = re.match('(pypi:|[^:]+://pypi.python.org/pypi/)(?P<id>[^/]+)', uri)
			return {
				'type': cls.upstream_type,
				'id': match.group('id')
			}
		except StandardError as e:
			logging.debug(e, exc_info=True)
			raise ValueError("can't parse pypi project from %s" % (uri,))

	@property
	def _releases(self):
		for v, info in self._info['releases'].items():
			info = [i for i in info if i['packagetype'] == 'sdist']
			if not info:
				logging.debug("No source release for %s" % v)
				continue
			v = composite_version.try_parse(v)
			yield v, Release(self, v, info[0], self._info)

	@cached_property
	def homepage(self): return self._info['info']['home_page']
	@cached_property
	def summary(self): return self._info['info']['summary']
	@cached_property
	def description(self): return self._info['info']['description']
