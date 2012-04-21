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
		return max(self.versions, key = Version)
	def updated_since(self, version):
		return Version(version) < Version(self.latest_version)
