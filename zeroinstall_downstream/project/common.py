from __future__ import absolute_import
import requests
import sys
import json
import logging
from .. import composite_version

def cached_property(fn):
	result = []
	def get(self):
		if not hasattr(self, '_property_cache'):
			self._property_cache = {}
		try:
			return self._property_cache[fn.__name__]
		except KeyError:
			val = fn(self)
			self._property_cache[fn.__name__] = val
			return val
	return property(get)

class Implementation(object):
	archive_type = None
	def __init__(self, **kw):
		for k, v in kw.items():
			setattr(self, k, v)
		assert isinstance(self.version, composite_version.CompositeVersion), "expected CompositeVersion object, got %s" % (type(self.version),)

class BaseProject(object):
	def __init__(self, id):
		self.id = id

	@cached_property
	def latest_version(self):
		if len(self.versions) == 0:
			raise RuntimeError("no versions found")
		return max(self.versions)

	@cached_property
	def latest_release(self):
		return self.implementation_for(self.latest_version)

	@cached_property
	def versions(self):
		return list(
			filter(lambda x: x is not None,
				map(composite_version.try_parse,
					self.version_strings)))

	def find_version(self, version_string):
		for version in self.versions:
			if version.fuzzy_match(version_string):
				return version
		raise AssertionError("No such version: %s" % (version_string,))
	
	@property
	def global_id(self): return "%s:%s" % (self.upstream_type, self.id)

	def __eq__(self, other): return type(self) == type(other)
	def __neq__(self, other): return not self.__eq__(other)
	def __hash__(self): return hash(self.id)
	def __cmp__(self, other): return cmp(self.global_id, other.global_id)

def getjson(*a, **k):
	response = requests.get(*a, **k)
	assert response.ok, response.content
	return json.loads(response.content)
