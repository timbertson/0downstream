import xmlrpclib
import datetime
from .common import cached_property, Implementation, BaseProject

class Pypi(BaseProject):
	upstream_type = 'pypi'
	def __init__(self, id):
		self.id = id
		self.upstream_id = id
		self.client = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
	
	@cached_property
	def versions(self):
		return self.client.package_releases(self.id)

	@cached_property
	def _release_data(self):
		return self.client.release_data(self.id, self.latest_version)

	@cached_property
	def homepage(self): return self._release_data['home_page']
	@cached_property
	def summary(self): return self._release_data['summary']
	@cached_property
	def description(self): return self._release_data['description']
	@cached_property
	def latest_release(self):
		info = self.client.release_urls(self.id, self.latest_version)
		print repr(info)
		info = filter(lambda x: x['packagetype'] == 'sdist', info)
		if len(info) == 0:
			raise ValueError("no `sdist` downloads found")
		info = info[0]
		print repr(dir(info['upload_time']))
		print repr(dir(info['upload_time'].value))
		released = datetime.datetime(*info['upload_time'].timetuple()[:6])
		return Implementation(version=self.latest_version, url=info['url'], released=released.strftime("%Y-%m-%d"), archive_type=None)



