from __future__ import print_function
import os
import re
import logging
import subprocess
import sys
import tempfile
import shutil
import stat
import json
import shlex

logger = logging.getLogger('zeroinstall_downstream.conf')

from zeroinstall_downstream import api
from zeroinstall_downstream.api import Tag, Attribute, COMPILE_NAMESPACE

type_formats = {
	'pypi':'python-%s.xml',
	'rubygems':'rubygems-%s.xml',
	'npm':'node-%s.xml',
}

FEED_URL_ROOT = 'http://gfxmonk.github.io/0downstream/feeds/'
FEED_PATH = 'feeds'

NODEJS_FEED = 'http://gfxmonk.net/dist/0install/node.js.xml'
BASH_FEED = 'http://repo.roscidus.com/utils/bash'
PYTHON_FEED = 'http://repo.roscidus.com/python/python'
DEV_NULL = open(os.devnull)

python3_blacklist = set([])

def feed_modified(path):
	subprocess.check_call(['0publish', '--key', '0downstream', '--xmlsign', path])

def resolve_project(project):
	type = project.upstream_type
	id = project.id

	#XXX: remove hack
	if (type, id) == ('npm', 'tap'): return None

	rel_path = os.path.join(type, id + '.xml')
	return api.FeedLocation(url=FEED_URL_ROOT + rel_path, path=os.path.join(FEED_PATH, rel_path))

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
		env = kw.get('env', os.environ).copy()
		try:
			del env['DISPLAY']
		except KeyError: pass
		kw['env'] = env
		subprocess.check_call(cmd, **kw)

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
		def run_check(args, pre_args=[], **kw):
			# first, dump `env` into a null-separated file
			with tempfile.NamedTemporaryFile(prefix='0downstream-', suffix='.env') as env_file:
				# sudo doesn't preserve all envs. So we manually reproduce `env` within sudo.
				# If something relies on specific userss etc it will fail, but mostly things
				# should just need a sane $PYTHONPATH, etc.
				# TODO: there is a lot of potential leakage here (eg `foo` being on $PATH because it's on mine.
				# consider using docker or some other sandbox to fix this.

				# run_feed(oenv, pre_args + [feed, '-x', SANDBOX_SUDO_WRAPPER, '--console', '--'] + args, **kw)
				run_feed(oenv, pre_args + [feed, '--console', '--', 'env', '--null'], stdout=env_file)
				allow_read_access(env_file.name)
				run_in_sandbox(['python', '-c', '''
from __future__ import print_function
import os,sys
# print(repr(sys.argv))
args=sys.argv[2:]
with open(sys.argv[1]) as env:
	for line in env.read().split('\\0'):
		if not line: continue
		k,v=line.split('=', 1)
		# print("setting %s=%r" % (k,v))
		os.environ[k]=v
os.execvp(args[0], args)
''', env_file.name] + args, **kw)

		try:
			if project.upstream_type == 'pypi':
				#XXX: https proxy doesn't work with CONNECT yet
				env = os.environ.copy()
				try:
					del env['https_proxy']
				except KeyError: pass

				# TODO: PYTHONPATH is not preserved by sudo
				run_check(['python', '-c', 'import sys;print repr(sys.path);import %s' % (project.id)],
						pre_args = [PYTHON_FEED, '--executable-in-path=python', '-a'],
						env=env)
			elif project.upstream_type == 'npm':
				run_check(['0install', 'run', current_selections_for(NODEJS_FEED), '-e', 'require("%s")' % (project.id)])
			elif project.upstream_type == 'rubygems':
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
	projects = [project]

	if project.upstream_type == 'pypi':
		requires_python_tag = Tag('requires', {'interface':PYTHON_FEED})

		# pypi doesn't have project metadata. So run python and extract it
		def get_metadata(python_verspec):
			#XXX run in sandbox
			detect_feed = os.path.join(os.path.dirname(__file__), 'tools/detect-python-metadata.xml')
			try:
				output = subprocess.check_output(['0install', 'run', '--version-for=' + PYTHON_FEED, python_verspec, detect_feed], cwd=project.working_copy)
			except subprocess.CalledProcessError as e:
				logger.warn("metadata extraction failed:", exc_info=True)
				return None
			else:
				return json.loads(output)

		info_2 = get_metadata('2..!3')
		project_infos = [info_2]

		if not project._release.supports_python_3:
			logger.info("project does not support python 3")
			python2_dep = requires_python_tag.copy()
			python2_dep.children.append(Tag('version', {'before':'3'}))
			project.add_to_impl(python2_dep)
		else:
			logger.info("project supports python 3")
			info_3 = get_metadata('3..!4')
			project_infos.append(info_3)
			
			if info_2 is None:
				if info_3 is None:
					raise RuntimeError("Couldn't extract project metadata")
				else:
					logger.info("Feed appears to only support python 3")
					# it's the future: we support py3 but not 2
					python_dep = requires_python_tag.copy()
					python_dep.children.append(Tag('version', {'not-before':'3'}))
					project.add_to_impl(python_dep)
					project_infos = [info_3]
			else: # info_2 is present
				if info_2 == info_3 and not info_2['use_2to3']:
					logger.info("Feed appears to support both python 2 and 3 without compilation")
					project.add_to_impl(requires_python_tag.copy())
				else:
					assert info_3 is not None, "couldn't get python3 metadata"
					logger.info("Creating separate python 2 & 3 implementations")
					# we need two different implementations
					project_3 = project.fork()
					projects.append(project_3)

					# implement py2 / py3 split
					project.set_implementation_id("py2_%s" % (project.version))
					python2_dep = requires_python_tag.copy()
					python2_dep.children.append(Tag('version', {'before':'3'}))
					project.add_to_impl(python2_dep)

					project_3.set_implementation_id("py3_%s" % (project.version))
					python3_dep = requires_python_tag.copy()
					python3_dep.children.append(Tag('version', {'not-before':'3'}))
					project_3.add_to_impl(python3_dep)

		for (project, info) in zip(projects, project_infos):
			project.guess_dependencies(info)
			project.create_dependencies()

			project.add_to_impl(Tag('environment', {'name':'PYTHONPATH', 'insert':'','mode':'prepend'}))
			portable_feed = project.generate_local_feed()

			# try running it as a "*-*" portable feed. if it works, we're good
			requires_build = not check_validity(project, portable_feed, cleanup=cleanup_actions)
			# if not, assume that it needs compilation. If this assumption is
			# incorrect, it'll fail later and we'll have to manually fix it anyway
			if requires_build:
				project.set_compile_properties(dup_src=True,
					command=
						Tag('command',{ 'name': 'compile' }, [
							Tag('runner', {'interface': 'http://gfxmonk.net/dist/0install/setup_py_0compile.xml'})
						])
				)

	elif project.upstream_type == 'npm':
		contents = os.listdir(project.working_copy)
		assert len(contents) == 1, "Expected 1 file in root of archive, got: %r" % (contents,)
		project.rename(contents[0], project.id)

		# project is in sane state - try figuring out dependencies
		project.guess_dependencies()
		project.create_dependencies()
	
		if project.id == 'mkfiletree':
			for req in project._release.runtime_dependencies:
				if req['interface'].endswith('rimraf.xml'):
					for child in req.children:
						if child.get('before') == '2.1':
							child['before'] = '2.2'

		nodejs_runner = Tag('runner', {'interface':NODEJS_FEED})
		project.add_to_impl(Tag('environment', {'name': 'NODE_PATH', 'insert':"", 'mode':"prepend"}))

		# figure out compilation:
		release_info = project.release_info
		requires_compilation = release_info.get('gypfile') == True
		# XXX nonlocal hack
		_requires_compilation = []

		def add_command(name, path, args=[]):
			rel_path = os.path.normpath(os.path.join(project.id, path))
			print(repr(os.listdir(os.path.dirname(os.path.join(project.working_copy, rel_path)))))
			print(name, path, args)
			if name == 'install':
				# XXX nonlocal hack
				_requires_compilation.append(True)
				return
			assert os.path.exists(os.path.join(project.working_copy, rel_path)), rel_path
			args = [Tag('arg', text=arg) for arg in args]
			project.add_to_impl(Tag('command',
				{
					'path': rel_path,
					'name': name
				},
				[nodejs_runner] + args
			))

		scripts = release_info.get('scripts', {})
		for name, command in scripts.items():
			args = shlex.split(command)
			rel_path = args.pop(0)
			assert name != 'run' # this might conflict with `bins`, below
			add_command(name, rel_path, args)

		bins = release_info.get('bin', {})
		if isinstance(bins, basestring):
			add_command('run', bins)
		else:
			for name, path in bins.items():
				if len(bins) == 1 or name == project.id:
					# this must be the canonical bin:
					name = "run"
				add_command(name, path)

		# XXX nonlocal hack
		requires_compilation = requires_compilation or bool(_requires_compilation)
		logger.info("requires_compilation = %r" % requires_compilation)
		if requires_compilation:
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

						Tag('requires', {'interface': FEED_URL_ROOT + 'node-node-gyp.xml'}, [
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

	else:
		assert False

	feed = project.generate_local_feed()
	while True:
		try:
			for project in projects:
				assert check_validity(project, feed, cleanup=cleanup_actions), "feed check failed"
			break
		except Exception as e:
			print("local feed: %s" % feed, file=sys.stderr)
			print("local extract: %s" % project.working_copy, file=sys.stderr)
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

def remove_indent(s):
	s = s.strip('\n')
	leading = re.match('( |\t)*', s).span()[1]
	return '\n'.join([line[leading:] for line in s.splitlines()])
