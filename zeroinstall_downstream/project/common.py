from __future__ import absolute_import
import requests
import sys
import json
import logging
from .. import composite_version
from ..archive import Archive

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
		return self.get_release(self.latest_version)

	@cached_property
	def versions(self):
		return list(self.releases.keys())
	
	@cached_property
	def releases(self):
		rv = {}
		for v, rel in self._releases:
			if v is not None:
				rv[v] = rel
		return rv

	def get_release(self, v):
		return self.releases[v]

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
	def __str__(self): return self.global_id

def getjson(*a, **k):
	response = requests.get(*a, **k)
	assert response.ok, response.content
	return json.loads(response.content)

class BaseRelease(object):
	@cached_property
	def working_copy(self):
		return self.archive.local

	def __enter__(self):
		self._enter_archive()
		return self

	def __exit__(self, *a):
		self.archive.__exit__(*a)

	def _enter_archive(self, **k):
		archive = self.archive = Archive(self.url, **k)
		archive.__enter__()
		return archive
