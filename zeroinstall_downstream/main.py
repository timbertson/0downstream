#!/usr/bin/env python
import argparse
from zeroinstall_downstream.pypi import Pypi
from zeroinstall_downstream.github import Github

sources = {
	'pypi': Pypi,
	'github': Github
}

def run():
	parser = argparse.ArgumentParser()
	sub = parser.add_subparsers()
	parser_new = sub.add_parser('new', help='make a new feed')
	parser_new.set_defaults(func=new)
	parser_update = sub.add_parser('update', help='update an existing feed')
	parser_update.set_defaults(func=update)
	parser_check = sub.add_parser('check', help='check whether a feed is up to date')
	parser_check.set_defaults(func=check)

	parser_new.add_argument('source', help='upstream type', choices=sources.keys())
	parser_new.add_argument('id', help='package name (or "user/repo" for github)')
	parser_new.add_argument('feed', help='local feed file to create (must not exist)')
	parser_new.add_argument('--prefix', help='prefix location for uploaded feed')
	parser_update.add_argument('feed', help='local zeroinstall feed file')
	parser_check.add_argument('feed', help='local or remote zeroinstall feed file')

	args = parser.parse_args()
	print repr(args)
	args.func(args)

def new():
	pass

def update():
	pass

def check():
	pass

if __name__ == '__main__':
	run()
