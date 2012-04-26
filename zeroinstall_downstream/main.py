#!/usr/bin/env python
import argparse
from zeroinstall_downstream.project import SOURCES
from zeroinstall_downstream.feed import Feed

def run():
	parser = argparse.ArgumentParser()
	sub = parser.add_subparsers()
	parser_new = sub.add_parser('new', help='make a new feed')
	parser_new.set_defaults(func=new)
	parser_update = sub.add_parser('update', help='update an existing feed')
	parser_update.set_defaults(func=update)
	parser_check = sub.add_parser('check', help='check whether a feed is up to date')
	parser_check.set_defaults(func=check)

	parser_new.add_argument('source', help='upstream type', choices=SOURCES.keys())
	parser_new.add_argument('id', help='package name (or "user/repo" for github)')
	parser_new.add_argument('feed', help='local feed file to create (must not exist)')
	parser_new.add_argument('--prefix', help='prefix location for uploaded feed')
	parser_update.add_argument('feed', help='local zeroinstall feed file')
	parser_check.add_argument('feed', help='local or remote zeroinstall feed file')

	args = parser.parse_args()
	print repr(args)
	return args.func(args)

def new(opts):
	cls = SOURCES[opts.source]
	project = cls(id=opts.id)
	opts.feed = os.path.expanduser(opts.feed)
	filename = os.path.basename(opts.feed)
	feed = Feed.from_project(project, opts.prefix)
	feed.add_latest_implementation()
	feed.save(opts.feed)

def update(opts):
	assert os.path.exists(opts.feed)
	with open(opts.feed, 'rw') as file:
		feed = Feed.from_file(file)
		feed.add_latest_implementation()
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
	if feed.needs_update():
		print "feed %s is outdated - new version %s is available" % (opts.feed, feed.latest_version())
		return 1
	else:
		print "feed %s is up to date" % (opts.feed,)

if __name__ == '__main__':
	sys.exit(run())
