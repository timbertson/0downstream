import re
import operator

import json
import logging

from .common import cached_property, Implementation, BaseProject, getjson
from .. import composite_version

class Release(object):
	def __init__(self, project, version_info):
		self.info = version_info
		self.version = composite_version.try_parse(version_info['version'])
		self.url = version_info['dist']['tarball']
		self.released = project._project_info['time'][self.version.upstream][:10]
	
	@property
	def implementation(self):
		return Implementation(version=self.version, url=self.url, released=self.released)

class Npm(BaseProject):
	upstream_type = 'npm'
	base = 'http://registry.npmjs.org/'

	@property
	def url(self):
		return 'https://npmjs.org/package/' + self.id
	
	@cached_property
	def _project_info(self):
		return getjson(self.base + '/' + self.id)

	@cached_property
	def _version_info(self):
		return self._project_info['versions']

	@cached_property
	def summary(self):
		return self._project_info['name'] + " npm package"

	@cached_property
	def description(self):
		return self._project_info['description']

	@cached_property
	def homepage(self):
		return self.url

	@cached_property
	def versions(self):
		return list(self._version_objects.keys())

	@cached_property
	def _version_objects(self):
		res = {}
		for v in self._version_info.values():
			val = Release(self, v)
			if val.version is not None:
				res[val.version] = val
		return res

	def implementation_for(self, version):
		return self._version_objects[version].implementation
	
	@classmethod
	def parse_uri(cls, uri):
		try:
			match = re.match('[^:]+://npmjs.org/(?P<id>[^/]+)', uri)
			return {
				'type': cls.upstream_type,
				'id': match.group('id')
			}
		except StandardError as e:
			logging.debug(e, exc_info=True)
			raise ValueError("can't parse npm project from %s" % (uri,))

