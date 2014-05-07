import re
import logging
import datetime
from .common import cached_property, Implementation, BaseProject, BaseRelease, getjson
from .. import composite_version
from ..archive import Archive
from ..tag import Tag

class Release(BaseRelease):
	def __init__(self, project, version, info):
		super(Release, self).__init__()
		self.version = version
		self.released = info['upload_time'][:10]
		self.info = info
		self.url = info['url']

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
			yield v, Release(self, v, info[0])

	@cached_property
	def homepage(self): return self._info['info']['home_page']
	@cached_property
	def summary(self): return self._info['info']['summary']
	@cached_property
	def description(self): return self._info['info']['description']
