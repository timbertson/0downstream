import re

import requests
import json

from .common import cached_property, Implementation, BaseProject

def get(*a, **k):
	response = requests.get(*a, **k)
	assert response.ok, response.content
	print (response.content)
	return json.loads(response.content)

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
		return get(self.info['commit']['url'])['commit']
	@property
	def released(self):
		return self.commit_info['author']['date'][:10]

class Github(BaseProject):
	upstream_type = 'github'
	def __init__(self, id):
		self.id = id
		self.upstream_id = id
		self.base = 'https://api.github.com/repos/' + id
	
	@cached_property
	def tags(self):
		return map(Tag, get(self.base + '/' + 'tags'))
	
	@cached_property
	def version_tags(self):
		d = {}
		for tag in self.tags:
			d[tag.version] = tag
		return d

	@cached_property
	def versions(self):
		return self.version_tags.keys()

	@cached_property
	def latest_release(self):
		return self.version_tags[self.latest_version].implementation
	
	@cached_property
	def repo_info(self):
		return get(self.base)

	@cached_property
	def homepage(self): return self.repo_info['html_url']

	@cached_property
	def summary(self): return self.repo_info['description']

	@cached_property
	def description(self): return self.summary



