#!/usr/bin/env python
import os, sys
import argparse
import logging
from zeroinstall_downstream.project import guess_project, SOURCES
from zeroinstall_downstream.feed import Feed

def run():
	parser = argparse.ArgumentParser()
	parser.add_argument('--debug', action='store_true')
	sub = parser.add_subparsers()
	parser_new = sub.add_parser('new', help='make a new feed')
	parser_new.set_defaults(func=new)
	parser_update = sub.add_parser('update', help='update an existing feed')
	parser_update.set_defaults(func=update)
	parser_check = sub.add_parser('check', help='check whether a feed is up to date')
	parser_check.set_defaults(func=check)
	parser_list_versions = sub.add_parser('list-versions', help='list the available versions of a feed')
	parser_list_versions.set_defaults(func=list_versions)

	parser_new.add_argument('url', help='url of the upstream project\'s page (from one of %s)' % ", ".join(sorted(SOURCES.keys())))
	parser_new.add_argument('feed', help='local feed file to create (must not exist)')
	parser_new.add_argument('--prefix', help='prefix location for uploaded feed', required=True)
	parser_new.add_argument('--force', '-f', help='overwrite any existing feed file', action='store_true')
	parser_update.add_argument('feed', help='local zeroinstall feed file')
	parser_update.add_argument('--info', action='store_true', dest='just_info', help='update project info only')
	parser_update.add_argument('--version', action='store_true', help='publish a specific version, not the newest')
	parser_check.add_argument('feed', help='local or remote zeroinstall feed file')
	parser_check.add_argument('--all', action='store_true', help='check for any unpublished versions, not just the newest')
	parser_list_versions.add_argument('feed', help='local or remote zeroinstall feed file')

	args = parser.parse_args()
	if args.debug:
		logging.getLogger().setLevel(logging.DEBUG)
		logging.debug("debug mode enabled")
	return args.func(args)

def new(opts):
	project = guess_project(opts.url)
	opts.feed = os.path.expanduser(opts.feed)
	if not opts.force and os.path.exists(opts.feed):
		print "feed %s already exists - use --force to overwrite it"
		return 1
	filename = os.path.basename(opts.feed)
	destination_url = opts.prefix.rstrip('/') + '/' + filename
	feed = Feed.from_project(project, destination_url)
	feed.add_implementation()
	with open(opts.feed, 'w') as outfile:
		feed.save(outfile)

def update(opts):
	assert os.path.exists(opts.feed)
	with open(opts.feed, 'r+') as file:
		feed = Feed.from_file(file)
		if not opts.just_info:
			feed.add_implementation(version=opts.version)
		file.seek(0)
		feed.save(file)

import contextlib
def _feed_from_path(path):
	if os.path.exists(path):
		ctx = open(path)
	else:
		assert '://' in path, "file does not exist (and does not look like a URL): %s" % (path,)
		ctx = contextlib.closing(urllib.urlopen(path))
	with ctx as file:
		return Feed.from_file(file)

def check(opts):
	feed = _feed_from_path(opts.feed)
	new_versions = feed.unpublished_versions(newest_only = not opts.all)
	if new_versions:
		print "feed %s is missing an implementation for version %s" % (opts.feed, ", ".join(sorted(new_versions)))
		return 1
	else:
		print "feed %s is up to date" % (opts.feed,)

if __name__ == '__main__':
	sys.exit(run())
