import os
import re
import json
import logging
from version import Version, VersionComponent
logger = logging.getLogger(__name__)

NODEJS_FEED = 'http://gfxmonk.net/dist/0install/node.js.xml'

def process_implementation(data):
	logger.debug("Processing implementation: %r" % (data,))
	implementation = data['implementation']
	archive = data['archive']
	config = data['config']
	feed = data['feed']
	project = data['project']

	_process_archive(archive, project.id)
	root = os.path.join(archive.local, project.id)

	with open(os.path.join(root, 'package.json')) as json_file:
		package_info = json.load(json_file)
	
	for requires in _get_requires(feed, package_info, config):
		implementation.appendChild(requires)
	for binding in _get_bindings(package_info, root, feed.doc, config):
		implementation.appendChild(binding)

def _process_archive(archive, package_id):
	'''NPM serves up packages with a single (meaningless) root directory
	like "package", or some hash. We rename this to <packagename>, so
	we get a path on $NODE_PATH that goes [PATH]/packagename>/index.json
	'''
	contents = os.listdir(archive.local)
	assert len(contents) == 1, "Expected 1 file in root of archive, got: %r" % (contents,)
	archive.rename(contents[0], package_id)

def _get_requires(feed, package_info, config):
	tags = []
	def restrict_version(tag, spec):
		version_info = list(_parse_version_info(spec))
		if version_info:
			version_tag = feed.doc.createElement('version')
			for (attr, ver) in version_info:
				version_tag.setAttribute(attr, str(ver))
			tag.appendChild(version_tag)
	
	def add_tag(tag_name, name, version_spec):
		iface = config.dependency_url(feed.project, name)
		if iface is None:
			logger.info("Ignoring dependency on %s" % (name,))
			return
		tag = feed.doc.createElement(tag_name)
		package_tag = feed.createUpstreamElement()
		package_tag.setAttribute("id", name)
		tag.appendChild(package_tag)

		tag.setAttribute('interface', iface)
		logger.debug("Processing version spec %s for %s" % (version_spec, name))
		restrict_version(tag, version_spec)
		tags.append(tag)
		return tag

	for (name, version_spec) in package_info.get('dependencies', {}).items():
		add_tag('requires', name, version_spec)

	for (name, version_spec) in package_info.get('optionalDependencies', {}).items():
		tag = add_tag('restricts', name, version_spec)
		if tag:
			tag.setAttribute('importance', 'recommended')

	for (name, version_spec) in package_info.get('peerDependencies', {}).items():
		add_tag('restricts', name, version_spec)
	
	return tags

def _get_bindings(package_info, root, document, config):
	env = document.createElement('environment')
	env.setAttribute('insert', '')
	env.setAttribute('mode', 'prepend')
	env.setAttribute('name', 'NODE_PATH')
	yield env

	bins = package_info.get('bin', {})
	if isinstance(bins, basestring):
		bins = {package_info['name']: bins}

	for name, rel_path in bins.items():
		cmd = document.createElement('command')
		cmd.setAttribute('path', re.sub('^\/\/', '', rel_path))
		cmd.setAttribute('name', name)
		runner = document.createElement('runner')
		runner.setAttribute('interface', NODEJS_FEED)
		cmd.appendChild(runner)
		yield cmd

def _parse_version_info(spec):
	# https://npmjs.org/doc/json.html#dependencies
	def parse(v):
		v = v.lstrip('v')
		# drop wildcard revisions
		v = re.sub('\.x.*', '', v)

		try:
			return Version.parse(v, coerce=True)
		except StandardError as e:
			logger.warn("Couldn't parse version string: %s" % (v,))
			return None
	
	def inc(v, levels=1):
		if v is None: return v
		return v.increment(levels)
	
	if spec == '' or spec == '*':
		return []
	if spec.startswith('git') or '://' in spec:
		logger.warn("Unparseable version spec: %s - just using first component" % (spec,))
		return _parse_version_info(spec.split('||')[0].strip())
	if '||' in spec:
		logger.warn("Unparseable version spec: %s" % (spec,))
		return []

	# OK, we have a potentially-parseable dependency spec:

	#strip spaces
	spec = re.sub(' ','', spec)
	parts = list(filter(lambda x: x.strip(), re.split('(<=|>=|[<>=~])', spec)))
	logging.debug("got version spec parts: %r" % (parts,))
	restrictions = []
	def add(op, ver):
		if ver is not None:
			restrictions.append((op, ver))

	if len(parts) == 1:
		number = parts.pop(0)
		# assume it's an exact version number
		if spec.startswith('='): spec = spec[1:]
		v = parse(spec)
		add('not-before', v)
		add('before', inc(v))

	assert len(parts) % 2 == 0, "Expected an even number of version parts, got: %r" % (parts,)
	while len(parts) > 1:
		op = parts.pop(0)
		number = parts.pop(0)

		if op == '<': add('before', parse(number))
		elif op == '>': add('not-before', inc(parse(number)))
		elif op == '<=': add('before', inc(parse(number)))
		elif op == '>=': add('not-before', parse(number))
		elif op == '~':
			v = parse(number)
			if v is not None:
				add('not-before', v)

				# make sure it's got exactly 2 components,
				# so that we increment the minor version
				components = v.components
				while(len(components) < 2): components.append(VersionComponent(0))
				upper_version = Version(components = components[:2]).increment()
				add('before', upper_version)
		else:
			logging.warn("Unknown version op: %s" % (op,))
	
	logger.debug("restrictions: %r" % (restrictions,))
	return restrictions

