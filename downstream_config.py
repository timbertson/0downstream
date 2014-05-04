from __future__ import print_function
import os
import re
import logging
import subprocess
import sys
import tempfile
import shutil
import stat

logger = logging.getLogger('zeroinstall_downstream.conf')

from zeroinstall_downstream import api
from zeroinstall_downstream.api import Tag, Attribute, COMPILE_NAMESPACE

type_formats = {
	'pypi':'python-%s.xml',
	'rubygems':'rubygems-%s.xml',
	'npm':'node-%s.xml',
}

FEED_URL_ROOT = 'http://gfxmonk.net/dist/0install/'
FEED_PATH = 'feeds'

NODEJS_FEED = 'http://gfxmonk.net/dist/0install/node.js.xml'
BASH_FEED = 'http://repo.roscidus.com/utils/bash'
DEV_NULL = open(os.devnull)

python3_blacklist = set([])

def feed_modified(path):
	subprocess.check_call(['0repo', 'update'])

def resolve_project(project):
	type = project.upstream_type
	id = project.id

	if type == 'npm' and id.startswith('node-'):
		id = id[5:]

	#XXX: remove hack
	if (type, id) == ('npm', 'tap'): return None

	# if project.upstream_type == 'npm' and project.id == 'node-gyp':
	# 	return api.FeedLocation(NODEJS_FEED, path=None, command='node-gyp')

	filename = type_formats[type] % id
	return api.FeedLocation(url=FEED_URL_ROOT + filename, path=os.path.join(FEED_PATH, filename))

def local_path_for(url):
	if url.startswith(FEED_URL_ROOT):
		return os.path.join(FEED_PATH, url[len(FEED_URL_ROOT):])

def check_validity(project, generated_feed, cleanup):
	logging.info("Checking validity of local feed: %s" % generated_feed)
	def allow_read_access(path):
		st = os.stat(path)
		os.chmod(path, st.st_mode | stat.S_IROTH)

	def allow_write_access(path):
		st = os.stat(path)
		os.chmod(path, st.st_mode | stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)

	# SANDBOX_SUDO = ['sudo','-u','sandbox', 'XDG_CACHE_DIRS=%s:/var/cache' % os.path.expanduser('~/.cache')]
	SANDBOX_SUDO = ['sudo','-u','sandbox', '--preserve-env', '--set-home' ]
	SANDBOX_SUDO_WRAPPER = '--wrapper=' + ' '.join(SANDBOX_SUDO)
	def _run(cmd, **kw):
		logger.debug("Running: %s" % (cmd))
		subprocess.check_call(cmd, stdin=DEV_NULL, **kw)

	def current_selections_for(feed, command='run'):
		with tempfile.NamedTemporaryFile(mode='w+', delete=False) as sels:
			cleanup.append(lambda: os.remove(sels.name))
			# from xml.dom import minidom
			# doc = minidom.parseString(sels)
			# for sel in doc.documentElement.getElementsByTagName('selection'):
			# 	local_path = sel.getAttribute('local-path')
			# 	if local_path:
			# 		st = os.stat(local_path)
			# 		assert st.st_mode & stat.S_IROTH, "%s is not readable by the sandbox user" % local_path
			# print(sels)
			subprocess.check_call(['0install', 'select', '--command=' + (command or ''), '--xml', feed], stdout=sels)
			allow_read_access(sels.name)
			return sels.name


	def run_feed_in_sandbox(feed, args, **kw):
		_run(SANDBOX_SUDO + ['0install', 'run', '--offline', current_selections_for(feed)] + args, **kw)
			# _run(['0install', 'run', '-v'] + SANDBOX_SUDO_WRAPPER + [feed] + args, **kw)

	def run_feed(feed, args, **kw):
		_run(['0install', 'run', feed] + args, **kw)

	def run(args, **kw):
		_run(args, **kw)

	def run_in_sandbox(args, **kw):
		_run(SANDBOX_SUDO + args, **kw)
		# #XXX: don't use sandbox user's cache, use mine and then just wrap execution in --wrapper=sudo -u sandbox
		# proxy_cmd = ['env', 'http_proxy=%s' % (os.environ['http_proxy'])] if 'http_proxy' in os.environ else []
		# sudo = ['sudo','-u','sandbox', 'env', 'XDG_CACHE_DIRS=%s:/var/cache' % os.path.expanduser('~/.cache')]

		# cmd = []
		# try:
		# 	idx = args.index(SUDO_WRAPPER)
		# except ValueError:
		# 	cmd = sudo
		# else:
		# 	cmd = args[:idx] + ['--wrapper=%s' % ' '.join(sudo)] + args[idx+1] + cmd

		# if proxy:
		# 	cmd += proxy_cmd

		# cmd.extend(args)
		# logger.debug("Running: %s" % (sudo + args))
		# subprocess.check_call(cmd, stdin=DEV_NULL, **kw)
	
	oenv = 'http://gfxmonk.net/dist/0install/0env.xml'
	def check(feed):
		# sels = current_selections_for(feed)
		def run_check(args):
			run_feed(oenv, ['-x', SANDBOX_SUDO_WRAPPER, feed, '--console', '--'] + args)

		try:
			if project.type == 'pypi':
				run_check(['python', '-c', 'import %s' % (project.id)])
			elif project.type == 'npm':
				run_check(['0install', 'run', current_selections_for(NODEJS_FEED), '-e', 'require("%s")' % (project.id)])
			elif project.type == 'rubygems':
				run_check(['ruby', '-e', 'require("%s")' % (project.id)])
			else:
				assert False, "can't check feed validity"
		except subprocess.CalledProcessError as e:
			return False
		return True

	allow_read_access(generated_feed)

	if project.requires_compilation:
		# first compile it, then run the local feed
		ocompile = 'http://0install.net/2006/interfaces/0compile.xml'

		compile_root = tempfile.mkdtemp()

		# add a `finally` block to the enclosing scope
		# (delaying it means we can inspect the directory
		# interactively if something fails)
		def remove_tempdir():
			if os.path.exists(dest):
				# sandbox owns these files, need it to delete them
				run_in_sandbox(['rm', '-rf', dest])
			os.rmdir(compile_root)
		cleanup.append(remove_tempdir)

		# allow_write_access(compile_root)
		dest = os.path.join(compile_root, '0compile')
		logging.warn("Building in %s" % dest)
		run_feed(ocompile, ['setup', generated_feed, dest])

		# transfer to `sandbox` group, so sandbox user can write it
		run(['chgrp', '-R', 'sandbox', compile_root])
		run(['chmod', '-R', 'g+rwX', compile_root])

		run_feed_in_sandbox(ocompile, ['build'], cwd=dest)
		#TODO: we could do a `publish` here, if we plan to upload the binaries somewhere

		files = set(os.listdir(dest))
		# exclude expected file to get the output dir
		files.difference_update(set(['src','build','0compile.properties']))
		assert len(files) == 1, "expected 1 remaining file, got: %r" % (files,)
		built_feed = os.path.join(dest, files.pop(), '0install', 'feed.xml')
		return check(built_feed)
	else:
		return check(generated_feed)
	
def process(project):
	cleanup_actions = []
	project.template = project.ensure_template()
	project.guess_dependencies()
	project.create_dependencies()
	
	# compilation:
	if project.type == 'opam':
		assert False, 'todo'
	elif project.type == 'pypi':
		project.add_to_impl(Tag('environment', {'name':'PYTHONPATH', 'insert':'','mode':'prepend'}))
		portable_feed = project.generate_local_feed()

		# try running it as a "*-*" portable feed. if it works, we're good
		requires_build = not check_validity(project, portable_feed, cleanup=cleanup_actions)
		# if not, assume that it needs compilation. If this assumption is
		# incorrect, it'll fail later and we'll have to manually fix it anyway
		if requires_build:
			project.set_compile_properties(dup_src=True, command='''
				<command name="compile">
					<runner interface="http://repo.roscidus.com/utils/bash">
					<arg>-euxc</arg>
					python setup.py
					</arg>
				</command>
			''')
	elif project.type == 'npm':
		if project.id == 'mkfiletree':
			for req in project._release.runtime_dependencies:
				print(req)
				if req['interface'].endswith('node-rimraf.xml'):
					for child in req.children:
						if child.get('before') == '2.1':
							child['before'] = '2.2'

		nodejs_runner = Tag('runner', {'interface':NODEJS_FEED})
		project.add_to_impl(Tag('environment', {'name': 'NODE_PATH', 'insert':"", 'mode':"prepend"}))

		release_info = project.release_info
		if release_info.get('gypfile') == True:
			project.add_to_impl(
				Tag('requires', {'interface':NODEJS_FEED}, [
					Tag('version', None, children=[
						Attribute('compile:pin-components', '2', namespace=COMPILE_NAMESPACE)
					])
				])
			)
			project.set_compile_properties(
				dup_src=True,
				command=
					Tag('command', {'name':'compile'}, [

						Tag('requires', {'interface': 'http://gfxmonk.net/dist/0install/npm.xml'}, [
							Tag('executable-in-var', {'name':'NPM'})
						]),

						Tag('requires', {'interface': FEED_URL_ROOT + 'node-gyp.xml'}, [
							Tag('executable-in-var', {'name':'NODE_GYP'})
						]),

						Tag('runner', {'interface': BASH_FEED}, [
							Tag('arg', text='-euxc'),
							Tag('arg', text='''
								cd "$BUILDDIR/{project_id}"
								"$NPM" build .
								cp -a "$BUILDDIR/{project_id}" "$DISTDIR/"

								# remove some common unnecessary files
								cd "$DISTDIR/{project_id}"
								rm -rf src test deps
							'''.format(project_id=project.id)),
						])
					]),
			)
			# do this again now that we've marked the feed as needing compilation
			project.create_dependencies()

		bins = release_info.get('bin', {})
		if isinstance(bins, basestring):
			bins = {project.release_info['name']: bins}

		for name, rel_path in bins.items():
			if len(bins) == 1:
				name = "run"
			rel_path = os.path.normpath(os.path.join(project.id, rel_path))
			assert os.path.exists(os.path.join(project.working_copy, rel_path))
			project.add_to_impl(Tag('command',
				{
					'path': rel_path,
					'name': name
				},
				[nodejs_runner]
			))

	else:
		assert False

	feed = project.generate_local_feed()
	while True:
		try:
			assert check_validity(project, feed, cleanup=cleanup_actions), "feed check failed"
			break
		except Exception as e:
			print("local feed: %s" % feed, file=sys.stderr)
			print("local extract: %s" % project._release.archive.local, file=sys.stderr)
			print("%s: %s" % (type(e).__name__, e))
			if not sys.stdin.isatty():
				raise

			# before we go cleaning everything up,
			# give the user a chance to inspect / fix things manually
			while True:
				print("What next? (q)uit / (r)etry / (p)db: ", file=sys.stderr, end='')
				response = raw_input()
				if response: response = response.lower()
				if response == 'q' or not response:
					raise
				elif response == 'r':
					break
				elif response == 'p':
					import pdb;
					pdb.set_trace()
					break
				print("eh?", file=sys.stderr)
		finally:
			err = None
			for action in cleanup_actions:
				try:
					action()
				except Exception as e:
					logging.error("Error during cleanup:", exc_info=True)
					if err is None:
						err = e
			cleanup_actions = []
			if err:
				raise err

