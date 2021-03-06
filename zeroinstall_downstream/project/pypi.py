import re
import logging
import xmlrpclib
import datetime
from .common import cached_property, Implementation, BaseProject

class Pypi(BaseProject):
	upstream_type = 'pypi'
	def __init__(self, id):
		self.id = id
		self.upstream_id = id
		self.client = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')

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

	@cached_property
	def version_strings(self):
		return self.client.package_releases(self.id)

	@cached_property
	def _release_data(self):
		return self.client.release_data(self.id, self.latest_version.upstream)

	@cached_property
	def homepage(self): return self._release_data['home_page']
	@cached_property
	def summary(self): return self._release_data['summary']
	@cached_property
	def description(self): return self._release_data['description']
	def implementation_for(self, version):
		info = self.client.release_urls(self.id, version.upstream)
		info = filter(lambda x: x['packagetype'] == 'sdist', info)
		if len(info) == 0:
			raise ValueError("no `sdist` downloads found")
		info = info[0]
		released = datetime.datetime(*info['upload_time'].timetuple()[:6])
		return Implementation(version=version, url=info['url'], released=released.strftime("%Y-%m-%d"))



