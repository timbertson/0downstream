#!/usr/bin/env python
from __future__ import print_function
import os, sys
import argparse
import logging
import bdb
import json
from zeroinstall_downstream.project import guess_project, SOURCES
from zeroinstall_downstream.project import make as make_project
from zeroinstall_downstream.feed import Feed
from zeroinstall_downstream.composite_version import CompositeVersion
from zeroinstall_downstream import actions
from zeroinstall_downstream import proxy

prompt = getattr(__builtins__, 'raw_input', input)
EXPORT_VERSION = 1

def run():
	parser = argparse.ArgumentParser()
	parser.add_argument('--debug', action='store_true')
	sub = parser.add_subparsers()
	parser_add = sub.add_parser('add', help='add or update a feed (and all missing dependencies)')
	parser_add.add_argument('--version', '-v', help='add a specific version, not the newest')
	parser_add.add_argument('--interactive', '-i', help='select version interactively', action='store_true')
	parser_add.add_argument('--recursive', help='also update dependencies', action='store_const', const=actions.create)
	parser_add.add_argument('--recreate', help='regenerate feed (republishes each version with the current config)', action='store_true')
	parser_add.add_argument('--info', action='store_true', dest='just_info', help='update project info (existing feeds only)')
	parser_add.add_argument('specs', nargs='+', help='feed file or project identifier (upstream URL or <type>:<id>, for type in %s)' % ", ".join(sorted(SOURCES.keys())))
	parser_add.set_defaults(func=add)

	parser_check = sub.add_parser('check', help='check whether a feed is up to date')
	parser_check.set_defaults(func=check)
	parser_check.add_argument('--all', action='store_true', help='check for any unpublished versions, not just the newest')
	parser_check.add_argument('specs', nargs='+', help='feed file or project identifier')

	parser_list = sub.add_parser('list', help='list project / feed versions')
	parser_list.set_defaults(func=list_versions)
	parser_list.add_argument('specs', nargs='+', help='feed file or project identifier')

	parser_proxy = sub.add_parser('proxy', help='run a caching HTTP proxy, with unpublished feeds served directly from disk')
	parser_proxy.set_defaults(func=proxy.run)
	parser_proxy.add_argument('--max-age', '-a', type=int, help='max-age of cached resources, in hours. -1 == forever', default=24 * 7)
	parser_proxy.add_argument('--port', type=int, help='HTTP proxy port', default=8082)

	parser_export = sub.add_parser('export', help='export feed state (projects and versions) to JSON')
	parser_export.set_defaults(func=export_state)
	parser_export.add_argument('--force', '-f', action='store_true')
	parser_export.add_argument('dest')
	parser_export.add_argument('feeds', nargs='+', help='feeds to include in export')

	parser_import = sub.add_parser('import', help='recreate all feeds present in a previously-exported file')
	parser_import.set_defaults(func=import_state)
	parser_import.add_argument('file')

	args = parser.parse_args()
	if args.debug:
		logging.getLogger().setLevel(logging.DEBUG)
		logging.debug("debug mode enabled")
	else:
		logging.getLogger('zeroinstall_downstream').setLevel(logging.INFO)
		logging.getLogger('downstream_config').setLevel(logging.INFO)
	
	args.config = _load_config()
	try:
		return args.func(args)
	except (AssertionError, bdb.BdbQuit, EOFError, KeyboardInterrupt) as e:
		if isinstance(e, AssertionError):
			print('AssertionError: ' + str(e), file=sys.stderr)
		if args.debug:
			logging.error("", exc_info=True)
		sys.exit(2)

def _resolve(spec, opts):
	if os.path.isfile(spec):
		project = Feed.from_path(spec).guess_project()
		location = opts.config.resolve_project(project)
		assert os.path.samefile(spec, location.path), "feed at %s resolves to a different location: %s" % (spec, location.path)
	else:
		try:
			# if it's a feed URL inside our repo, we can get the project from our config
			local_path = opts.config.local_path_for(spec)
			assert local_path is not None and os.path.exists(local_path)
			project = Feed.from_path(local_path).guess_project()
		except (AssertionError,KeyError) as e:
			project = guess_project(spec)
		location = opts.config.resolve_project(project)
	assert location
	return (project, location)

def _load_config():
	confname = 'downstream_config'
	if not os.path.exists(confname + '.py'):
		assert False, "no %s.py" % confname

	import importlib
	here = os.path.abspath('.')
	sys.path.insert(0, here)
	try:
		return importlib.import_module(confname)
	finally:
		sys.path.remove(here)

def _assert_exists(path):
	assert os.path.exists(path), "no such file: %s" % path

def add(opts):
	if opts.recursive:
		assert not opts.version, "can't specify both --version and --recursive"
	
	if len(opts.specs) > 1:
		assert not opts.version, "can't specify --version with multiple projects"
	
	for spec in opts.specs:
		(project, location) = _resolve(spec, opts)
		exists = os.path.exists(location.path)

		if opts.interactive:
			for version in sorted(project.versions):
				print(' - %s' % version.upstream, file=sys.stderr)
			print()
			print('Enter version: ', file=sys.stderr, end='')
			opts.version = raw_input().strip()
			assert opts.version

		if opts.just_info:
			assert exists, location.path
			actions.update_info(project, location, opts.version, opts)
		else:
			if opts.recreate:
				assert exists, location.path
			action = (actions.update if exists else actions.create)
			action(project, location, opts.version, opts)

def _format_version(version):
	if version.exact: return version.upstream
	return "%s (%s)" % (version.derived, version.upstream)

def list_versions(opts):
	for spec in opts.specs:
		project, location = _resolve(spec, opts)

		feed = Feed.from_path(location.path)

		print("")
		print(" Version information for %s" % (location.path,))
		print(" %s\n" % (location.url,))
		_list_versions(feed, project)

def _list_versions(feed, project):
	feed_versions = set(map(CompositeVersion.from_derived, feed.published_versions))
	project_versions = set(project.versions)
	all_versions = feed_versions.union(project_versions)
	print(" +---- available at project page")
	print(" | +-- published in zeroinstall feed")
	print(" | |")
	print("------------------------")
	for version in sorted(all_versions):
		flag = lambda b: '+' if b else ' '
		print(" %s %s   version %s" % (
				flag(version in project_versions),
				flag(version in feed_versions),
				version.pretty()))


def check(opts):
	rv = 0
	for spec in specs:
		(project, location) = _resolve(opts.spec, opts)
		feed = Feed.from_path(location.path)

		new_versions = feed.unpublished_versions(project, newest_only = not opts.all)
		if new_versions:
			_list_versions(feed, project)
			print("")
			new_upstream_versions = ", ".join(sorted([v.upstream for v in new_versions]))
			print("feed %s\nis missing an implementation for version %s" % (location.path, new_upstream_versions))
			rv += 1
		else:
			print("up to date: %s" % (location.path,))
	return rv

def export_state(opts):
	assert opts.force or not os.path.exists(opts.dest), "destination already exists"
	state = {
		'version': EXPORT_VERSION,
	}
	feeds = []
	for path in opts.feeds:
		print("exporting %s" % path)
		feed = Feed.from_path(path)
		attrs = feed.get_upstream_attrs()
		assert make_project(**attrs) # ensure this is enough info to create the project
		feeds.append({'project': attrs, 'versions':list(map(str, feed.published_versions))})
	feeds = sorted(feeds, key=lambda info: (info['project']['type'], info['project']['id']))
	state['feeds'] = feeds
	with open(opts.dest, 'w') as f:
		json.dump(state, f, indent=2, sort_keys=True)
	
def import_state(opts):
	opts.recursive = actions.update
	with open(opts.file) as f:
		state = json.load(f)
	assert state['version'] == EXPORT_VERSION, "unsupported version"
	opts.recreate = state['feeds']

	for item in state['feeds']:
		project = make_project(**item['project'])
		location = opts.config.resolve_project(project)
		assert location is not None, "can't recreate project %r" % project
		actions.update(project, location, version=None, opts=opts)

if __name__ == '__main__':
	sys.exit(run())
