import re

import requests
import logging

from .common import cached_property, Implementation, BaseProject, getjson


#TODO: use this to get readme data
class Tree(object):
	def __init__(self, sha):
		pass

	@cached_property
	def files(self):
		pass

	@cached_property
	def readme(self):
		pass

class Tag(object):
	archive_type='application/x-compressed-tar'
	version_re = re.compile('^(v(ersion)?(. -)?)?(?=[0-9])', re.I)
	def __init__(self, info):
		self.info = info
	@property
	def name(self): return self.info['name']

	@property
	def url(self): return self.info['tarball_url']

	@property
	def is_version(self): return re.match(self.version_re, self.name)

	@property
	def version(self): return re.sub(self.version_re, '', self.name)

	@property
	def implementation(self):
		return Implementation(version=self.version, url=self.url, archive_type=self.archive_type, released=self.released, extract=None)

	@cached_property
	def commit_info(self):
		return getjson(self.info['commit']['url'])['commit']

	@property
	def released(self):
		return self.commit_info['author']['date'][:10]

class Github(BaseProject):
	upstream_type = 'github'
	def __init__(self, id):
		self.id = id
		self.upstream_id = id
		self.base = 'https://api.github.com/repos/' + id
	
	@classmethod
	def parse_uri(cls, uri):
		try:
			match = re.match('[^:]+://github.com/(?P<id>[^/]+/[^/]+)', uri)
			return {
				'type': cls.upstream_type,
				'id': match.group('id')
			}
		except StandardError as e:
			logging.debug(e, exc_info=True)
			raise ValueError("can't parse github project from %s" % (uri,))
	
	@cached_property
	def tags(self):
		return map(Tag, getjson(self.base + '/' + 'tags'))
	
	@cached_property
	def version_tags(self):
		d = {}
		for tag in self.tags:
			d[tag.version] = tag
		return d

	@cached_property
	def versions(self):
		return self.version_tags.keys()

	def implementation_for(self, version):
		return self.version_tags[version].implementation
	
	@cached_property
	def repo_info(self):
		return getjson(self.base)

	@cached_property
	def homepage(self): return self.repo_info['html_url']

	@cached_property
	def summary(self): return self.repo_info['description']

	@cached_property
	def description(self): return self.summary



