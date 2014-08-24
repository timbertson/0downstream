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

URL_ROOT = 'http://gfxmonk.github.io/0downstream/'
FILES_URL_ROOT = URL_ROOT + 'files/'
FEED_URL_ROOT = URL_ROOT + 'feeds/'
ROOT_PATH = os.path.join(os.path.dirname(__file__))
FEED_PATH = os.path.join(ROOT_PATH, 'feeds')

# ZEROINSTALL_BIN = '0install'
ZEROINSTALL_BIN = "/home/tim/dev/0install/zeroinstall/build/ocaml/0install"

NODEJS_FEED = 'http://gfxmonk.net/dist/0install/node.js.xml'
BASH_FEED = 'http://repo.roscidus.com/utils/bash'
PYTHON_FEED = 'http://repo.roscidus.com/python/python'
ZI_PUBLISH = 'http://0install.net/2006/interfaces/0publish'
COMPILE_OPAM_FEED = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tools','opam-src-build','opam-src-build.xml')) #XXX make public
OCAML_RUNTIME_FEED = 'http://repo.roscidus.com/ocaml/ocaml-runtime'
OCAML_COMPILER_FEED = 'http://gfxmonk.net/dist/0install/ocaml.xml'
DEV_NULL = open(os.devnull)

python3_blacklist = set([])

def pin_components(n):
	Attribute('compile:pin-components', str(n), namespace=COMPILE_NAMESPACE)

def feed_modified(path):
	api.run_0publish(['--key', '0downstream', '--xmlsign', path])

def resolve_project(project):
	type = project.upstream_type
	id = project.id

	#XXX: remove hack
	if (type, id) == ('npm', 'tap'): return None

	rel_path = os.path.join(type, id + '.xml')
	return api.FeedLocation(url=FEED_URL_ROOT + rel_path, path=os.path.join(FEED_PATH, rel_path))

def local_path_for(url):
	if url.startswith(URL_ROOT):
		return os.path.join(ROOT_PATH, url[len(URL_ROOT):])

def check_validity(project, generated_feed, cleanup, post_compile_hook=None):
	logging.info("Checking validity of local feed: %s" % generated_feed)

	def _run(cmd, **kw):
		logger.debug("Running: %s" % (cmd))
		env = kw.get('env', os.environ).copy()
		try:
			del env['DISPLAY']
		except KeyError: pass

		if project.upstream_type == 'pypi':
			#XXX: https proxy doesn't work with CONNECT yet
			try:
				del env['https_proxy']
			except KeyError: pass

		kw['env'] = env
		subprocess.check_call(cmd, **kw)

	def run_feed(feed, args, **kw):
		_run([ZEROINSTALL_BIN, 'run', feed] + args, **kw)

	def run(args, **kw):
		_run(args, **kw)

	oenv = 'http://gfxmonk.net/dist/0install/0env.xml'
	def check(feed):
		def run_check(args, pre_args=[], **kw):
			run_feed(oenv, pre_args + [feed, '--console', '--'] + args, **kw)

		try:
			if project.upstream_type == 'pypi':
				module_name = getattr(project, 'module_name', None)
				module_names = set(
					[module_name] if module_name is not None
					else [project.id.replace('-','_')]
				)

				fakes_feed = os.path.join(os.path.dirname(__file__), 'tools/fakes/python/fakes.xml')
				module_names.update([n.lower() for n in module_names])
				module_names.update([re.sub('_?python_?', '', n, flags=re.I) for n in module_names])

				# keep importing stuff until it works
				run_check(['python', '-c', '''
import importlib
err = None
for mod in %r:
	try:
		importlib.import_module(mod)
		err = None
	except ImportError as e:
		err = e
if err: raise err
''' % sorted(module_names)],
						pre_args = [PYTHON_FEED, '--executable-in-path=python', '-a', fakes_feed, '-a'])
			elif project.upstream_type == 'npm':
				run_check([ZEROINSTALL_BIN, 'run', NODEJS_FEED, '-e', 'require("%s")' % (project.id)])
			elif project.upstream_type == 'rubygems':
				run_check(['ruby', '-e', 'require("%s")' % (project.id)])
			elif project.upstream_type == 'opam':
				# there's no generic test we can do here, but if it's
				# successfully compiled then that's a good start.
				return True
			else:
				assert False, "can't check feed validity"
		except subprocess.CalledProcessError as e:
			return False
		return True

	if project.requires_compilation:
		# first compile it, then run the local feed
		ocompile = 'http://0install.net/2006/interfaces/0compile.xml'

		compile_root = tempfile.mkdtemp()

		# add a `finally` block to the enclosing scope
		# (delaying it means we can inspect the directory
		# interactively if something fails)
		def remove_tempdir():
			# XXX make this work for readonly files!
			shutil.rmtree(compile_root)
		cleanup.append(remove_tempdir)

		dest = os.path.join(compile_root, '0compile')
		logging.warn("Building in %s" % dest)
		run_feed(ocompile, ['setup', generated_feed, dest])

		# transfer to `sandbox` group, so sandbox user can write it
		run(['chgrp', '-R', 'sandbox', compile_root])
		run(['chmod', '-R', 'g+rwX', compile_root])

		run_feed(ocompile, ['build'], cwd=dest)
		#TODO: we could do a `publish` here, if we plan to upload the binaries somewhere

		files = set(os.listdir(dest))
		# exclude expected file to get the output dir
		files.difference_update(set(['src','build','0compile.properties']))
		assert len(files) == 1, "expected 1 remaining file, got: %r" % (files,)
		install_dir = files.pop()
		if post_compile_hook:
			post_compile_hook(os.path.join(dest, install_dir))
		built_feed = os.path.join(dest, install_dir, '0install', 'feed.xml')
		return check(built_feed)
	else:
		return check(generated_feed)
	
def process(project):
	cleanup_actions = []
	projects = [project]
	post_compile_hook = None

	if project.upstream_type == 'pypi':
		requires_python_tag = Tag('requires', {'interface':PYTHON_FEED})

		# pypi doesn't have project metadata. So run python and extract it
		def get_metadata(major_version):
			spec = '%d..!%d' % (major_version, major_version+1)
			#XXX run in sandbox
			detect_feed = os.path.join(os.path.dirname(__file__), 'tools/detect-python-metadata/detect-python-metadata.xml')

			scratch = tempfile.mkdtemp()
			#NOTE: detection of metadata will often cause the contents of `workdir` to change.
			# This is horrid, so we copy everything into a tempdir first
			try:
				tmp_dest = os.path.join(scratch, "contents")
				shutil.copytree(project.working_copy, tmp_dest, symlinks=True)
				try:
					output = subprocess.check_output([ZEROINSTALL_BIN, 'run', '--version-for=' + PYTHON_FEED, spec, detect_feed], cwd=tmp_dest)
				except subprocess.CalledProcessError as e:
					logger.warn("metadata extraction failed:", exc_info=True)
					return None
				else:
					# print('JSON OUTPUT: %r' % output)
					info = json.loads(output)
					# info['language_version'] = major_version
					# logger.info("Detected metadata: %r", info)
					if info['use_2to3']:
						# ignore use_2to3 setting for python2 implementations
						if language_version != 3:
							info['use_2to3'] = False

					scripts = info['scripts']
					script_names = set([script['name'] for script in scripts])
					for script in scripts[:]:
						name = script['name']
						trailing_version = re.search(r'-?\d+(\.\d+)+', name)
						if trailing_version:
							if name[:trailing_version.start()] in script_names:
								logger.info("removing extraneous version-stamped script %s" % (name))
								scripts.remove(script)
							else:
								logger.info("script name %r appears versioned, but there isn't an alternative in %r: %s" % (name, script_names))
					return info
			finally:
				shutil.rmtree(scratch)

		info_2 = get_metadata(2)
		project_infos = [info_2]

		if not project._release.supports_python_3:
			logger.info("project does not support python 3")
			python2_dep = requires_python_tag.copy()
			python2_dep.children.append(Tag('version', {'before':'3'}))
			project.add_to_impl(python2_dep)
		else:
			logger.info("project supports python 3")
			info_3 = get_metadata(3)
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
				if info_2 == info_3:
					logger.info("Feed appears to support both python 2 and 3 without compilation")
					project.add_to_impl(requires_python_tag.copy())
				else:
					assert info_3 is not None, "couldn't get python3 metadata"
					logger.info("Creating separate python 2 & 3 implementations, because:")
					for diff in diff_dicts(info_2, info_3):
						logger.info(" - " + diff)
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

					# for k,v in project.__dict__.items():
					# 	if getattr(project_3, k) is v:
					# 		logger.warn("SHARED %s: %r" % (k,v))

		for (project, info) in zip(projects, project_infos):
			project.guess_dependencies(info)
			project.create_dependencies()
			try:
				project.module_name = min(info['packages'], key=len)
			except ValueError:
				pass

			project.add_to_impl(Tag('environment', {'name':'PYTHONPATH', 'insert':'','mode':'prepend'}))

			assert not info['commands'], "TODO: don't know how to process pypi commands (only scripts)"
			scripts = info['scripts']
			if scripts:
				commands = set()
				script_dirs = set()

				def add_command(name, script):
					if name in commands:
						logger.warn("skipping duplicate %s (%r)" % (name, script))
						return False
					else:
						logger.info("adding command: %s", name)
					commands.add(name)

					if 'path' in script:
						# plain wrapper script
						path = script['path']
						tag = Tag('command',{ 'name': name, 'path': path}, [
							# XXX detect non-python wrapper scripts?
							Tag('runner', {'interface': PYTHON_FEED})
						])
						dir = os.path.dirname(path)
						if dir not in script_dirs:
							script_dirs.add(dir)
							project.add_to_impl(Tag('environment', {'name':'PATH', 'insert': dir,'mode':'prepend'}))

					else:
						mod = script['module']
						fn = script.get('fn', None)
						if fn:
							# ugh, setuptools. We need to import a module *and* call a specific function,
							# which isn't supported by the regular python interpreter.
							# XXX if this is too hacky we could write a wrapper, or use setuptools itself
							# (but I suspect setuptools is way more pain than gain)
							tag = Tag('command',{ 'name': name}, [
								Tag('runner', {'interface': PYTHON_FEED}, [
									Tag('arg', text='-c'),
									Tag('arg', text='import sys;sys.argv[0] = "' + script['name'] + '"; import ' + mod + ' as main; sys.exit(main.'+fn+'())'),
								])
							])
						else:
							# easy: a plain module runner
							tag = Tag('command',{ 'name': name}, [
								Tag('runner', {'interface': PYTHON_FEED}, [
									Tag('arg', text='-m'),
									Tag('arg', text=module),
								])
							])
					project.add_to_impl(tag)


				if len(scripts) > 1:
					# heuristic: pick the shortest command that
					# shares the longest prefix with the package name
					def score(script):
						name = script['name']
						namelen = len(name)
						common_chars = common_prefix(name, project.id)
						excess_chars = namelen - common_chars
						# include namelen as a tiebreaker,
						# when multiple commands have the same number of excess chars
						# (presumably 0)
						rv = (excess_chars, namelen)
						logger.debug("score for %s: %r", name, rv)
						return rv
					scripts = sorted(scripts, key=score)
					script_names = [script['name'] for script in scripts]
					logger.info("Selecting %r as main command (candidates: %r)", script_names[0], script_names)

				add_command('run', scripts[0])

				for script in scripts:
					add_command(script['name'], script)

			portable_feed = project.generate_local_feed()

			# try running it as a "*-*" portable feed. if it works, we're good
			has_native_code = any([
				info['has_c_libraries'],
				info['has_ext_modules'],
			])
			requires_build = any([
				has_native_code,
				info['use_2to3'],
			])
			
			if not requires_build and not check_validity(project, portable_feed, cleanup=cleanup_actions):
				# if the feed doesn't work as-is, assume that it needs compilation.
				# If this assumption is incorrect, it'll fail later and we'll have
				# to manually fix it anyway
				logger.info("portable feed failed - assuming compilation is required")
				requires_build = True

			if requires_build:
				# compiled implementations have their libs at lib/
				project.remove_from_impl(lambda t: isinstance(t, Tag) and t.get('name') == 'PYTHONPATH')
				project.add_to_impl(Tag('environment', {'name':'PYTHONPATH', 'insert':'lib','mode':'prepend'}))
				if has_native_code:
					# pin python version used to e.g. 2.7.*
					# this will duplicate the dependency on python, but that should be fine
					Tag('requires', {'interface':PYTHON_FEED}, [
						Tag('version', None, children=[
							pin_components(2),
						])
					])

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
						pin_components(2),
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

	elif project.upstream_type == "opam":
		project.guess_dependencies(ocaml_feed=OCAML_COMPILER_FEED)

		contents = os.listdir(project.working_copy)
		assert len(contents) == 1, "Expected 1 file in root of archive, got: %r" % (contents,)
		project.rename(contents[0], 'src')

		# add opam files:
		repo_path = 'opam'
		with open(os.path.join(os.path.dirname(__file__), 'files','opam-local-src'), 'rb') as f:
			opam_local_src_contents = f.read()

		project._release.add_opam_files(repo_path,
				src_url=FILES_URL_ROOT + 'opam-local-src',
				src_contents=opam_local_src_contents)

		project.set_compile_properties(dup_src=True,
			command=
				Tag('command',{ 'name': 'compile' }, [
					Tag('runner', {'interface': COMPILE_OPAM_FEED}),
					Tag('arg', text=project.id),
				]),
			children=[
				Tag('environment', {'name': 'OPAM_PKG_PATH', 'insert':repo_path, 'mode':"prepend"}),
				Tag('requires', {'interface': OCAML_COMPILER_FEED }),
			],
		)

		# needs to happen after we mark the implementation as compilable
		project.create_dependencies()

		def add_bins(root):
			blacklist = set(['safe_camlp4'])
			bindir = os.path.join(root, 'bin')
			if not os.path.exists(bindir):
				return

			bins = [f for f in os.listdir(bindir)
				if os.path.isfile(os.path.join(bindir,f)) and f not in blacklist
			]
			if not bins:
				return 

			commands = set()
			def add(name, filename):
				if name in commands: return
				commands.add(name)
				project.add_to_impl(Tag('command',
					{
						'path': 'bin/'+filename,
						'name': name
					},
				))

			for name in bins:
				filename = name
				if len(bins) == 1 or name == project.id:
					# this must be the canonical bin:
					name = "run"
				add(name, filename)

		post_compile_hook = add_bins

		# assert False, repr(project.release_info)

		# XXX process dependencies
	else:
		assert False, "unknown project type!"

	while True:
		feed = None
		try:
			for project in projects:
				feed = project.generate_local_feed()
				assert check_validity(
					project, feed, cleanup=cleanup_actions, post_compile_hook=post_compile_hook
				), "feed check failed"
			break
		except Exception as e:
			if feed is not None: print("local feed: %s" % feed, file=sys.stderr)
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

def error_cb(e):
	logger.error(e, exc_info=True)
	import pdb
	pdb.set_trace()

def common_prefix(*strings):
	import itertools
	def all_same(x):
		return all(x[0] == y for y in x)

	char_tuples = itertools.izip(*strings)
	prefix_tuples = itertools.takewhile(all_same, char_tuples)
	return len(list(prefix_tuples))

def remove_indent(s):
	s = s.strip('\n')
	leading = re.match('( |\t)*', s).span()[1]
	return '\n'.join([line[leading:] for line in s.splitlines()])

def diff_dicts(a,b):
	diff = []
	for k in set(a.keys()).union(set(b.keys())):
		if k in a and k in b:
			if a[k] != b[k]:
				diff.append("values for %s differ: %r != %r" % (k,a[k],b[k]))
		else:
			if k in a:
				diff.append("second dictionary lacks a value for %r" % (k,))
			else:
				diff.append("first dictionary lacks a value for %r" % (k,))
	return diff

