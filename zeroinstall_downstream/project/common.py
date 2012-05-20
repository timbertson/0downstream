import requests
import sys
import json
from version import Version

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
	def __init__(self, **kw):
		for k, v in kw.items():
			setattr(self, k, v)

class BaseProject(object):
	@cached_property
	def latest_version(self):
		if len(self.versions) == 0:
			raise RuntimeError("no versions found")

		def parse(s):
			try:
				return Version.parse(s)
			except ValueError, e:
				try:
					return Version.parse(s.replace('.rc', '-pre'))
				except ValueError: pass
				print >> sys.stderr, "WARNING: ignoring unparseable version %s: %s" % (s, e)
				return Version.parse('0')
		return max(self.versions, key = parse)

	def updated_since(self, version):
		return Version.parse(version) < Version.parse(self.latest_version)

def getjson(*a, **k):
	response = requests.get(*a, **k)
	assert response.ok, response.content
	return json.loads(response.content)
