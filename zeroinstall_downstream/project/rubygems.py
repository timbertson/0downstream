import re
import operator

import json
import logging

from .common import cached_property, Implementation, BaseProject, getjson
from .. import composite_version

class Release(object):
	archive_type = 'application/x-ruby-gem'
	def __init__(self, project, version_info):
		self.info = version_info
		self.version = composite_version.try_parse(version_info['number'])
		self.url = 'http://rubygems.org/gems/%s-%s.gem' % (project.id, self.version.upstream)
		self.released = version_info['built_at'][:10]
	
	@property
	def implementation(self):
		return Implementation(version=self.version, url=self.url, archive_type=self.archive_type, released=self.released)

class Rubygems(BaseProject):
	upstream_type = 'rubygems'
	base = 'https://rubygems.org/api/v1/'

	def __init__(self, id):
		self.id = id
		self.api_filename = "%s.json" % (id,)

	@property
	def url(self):
		return "https://rubygems.org/gems/" + self.id
	
	@cached_property
	def _project_info(self):
		return getjson(self.base + 'gems/' + self.api_filename)

	@cached_property
	def _version_info(self):
		return getjson(self.base + 'versions/' + self.api_filename)

	@cached_property
	def summary(self):
		# rubygems API provides no short description, so we synthesize a reasonable one:
		return self._project_info['name'] + " ruby gem"

	@cached_property
	def description(self):
		return self._project_info['info']

	@cached_property
	def homepage(self):
		return self._project_info['project_uri']

	@cached_property
	def versions(self):
		return list(self._version_objects.keys())

	@cached_property
	def _version_objects(self):
		res = {}
		for v in self._version_info:
			val = Release(self, v)
			if val.version is not None:
				res[val.version] = val
		return res

	def implementation_for(self, version):
		return self._version_objects[version].implementation
	
	@classmethod
	def parse_uri(cls, uri):
		try:
			match = re.match('(rubygems:|[^:]+://rubygems.org/gems/)(?P<id>[^/]+)', uri)
			return {
				'type': cls.upstream_type,
				'id': match.group('id')
			}
		except StandardError as e:
			logging.debug(e, exc_info=True)
			raise ValueError("can't parse rubygems project from %s" % (uri,))

