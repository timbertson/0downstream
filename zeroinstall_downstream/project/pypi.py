from __future__ import print_function
import re
import logging
import datetime
from .common import cached_property, Implementation, BaseProject, BaseRelease, getjson, try_parse_dep_version, add_version_op
from .. import composite_version
from ..archive import Archive
from ..tag import Tag
logger = logging.getLogger(__name__)

class Release(BaseRelease):
	def __init__(self, project, version, info, project_metadata):
		super(Release, self).__init__()
		self.project = project
		self.project_metadata = project_metadata
		self.version = version
		self.released = info['upload_time'][:10]
		self.info = info
		self.url = info['url']
		self.supports_python_3 = 'Programming Language :: Python :: 3' in project_metadata['info']['classifiers']
		self.runtime_dependencies = []
		#TODO: is there a separate source for these?
		self.compile_dependencies = self.runtime_dependencies
		self.dependency_names = set()
	
	def copy(self):
		return type(self)(project=self.project, version=self.version, info=self.info, project_metadata=self.project_metadata)
	
	def detect_dependencies(self, resolver, metadata):
		logger.debug("extract_depependencies: pypi petadata = %r", metadata)
		for requirement in metadata['install_requires']:
			match = re.match(r'^(?P<id>[-_a-zA-Z.]+)(\[(?P<extras>)\])?(?P<version_spec>.*)$', requirement)
			if not match:
				raise RuntimeError("Can't parse %s" % (requirement,))
			groups = match.groupdict()
			name = groups['id']
			extras = groups['extras']
			if extras:
				logger.warn("Can't handle extras: %s" % (extras,))
			version_spec = groups['version_spec'] or ""

			self.dependency_names.add(name)

			location = resolver(Pypi(name))
			if location is None:
				logger.info("Skipping dependency: %s" % (name,))
				return

			url = location.url
			tag = Tag('requires', {'interface': url})
			if location.command is not None:
				tag.attr('command', location.command)
			version_tag = _parse_version_info(version_spec)
			if version_tag is not None:
				tag.append(version_tag)
			self.runtime_dependencies.append(tag)


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
			logger.debug(e, exc_info=True)
			raise ValueError("can't parse pypi project from %s" % (uri,))

	@property
	def _releases(self):
		for v, info in self._info['releases'].items():
			info = [i for i in info if i['packagetype'] == 'sdist']
			if not info:
				logger.debug("No source release for %s" % v)
				continue
			v = composite_version.try_parse(v)
			yield v, Release(self, v, info[0], self._info)

	@cached_property
	def homepage(self): return self._info['info']['home_page']
	@cached_property
	def summary(self): return self._info['info']['summary']
	@cached_property
	def description(self): return self._info['info']['description']

def _parse_version_info(spec):
	# http://peak.telecommunity.com/DevCenter/setuptools#declaring-dependencies
	specs = map(lambda x: x.strip(), spec.split(','))
	specs = filter(None, specs)
	specs = list(specs)

	if not specs: return None

	restrictions = Tag('version')
	def add(attr, val):
		restrictions.attr(attr, str(val))

	for spec in specs:
		op, v = re.match(r'^([!=<>]+)\s*(\S+)$', spec).groups()
		v = try_parse_dep_version(v)
		if v is None:
			return None

		add_version_op(op, v, add=add)
	logger.debug("restrictions: %r" % (restrictions,))
	return restrictions

