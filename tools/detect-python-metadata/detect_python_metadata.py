from __future__ import print_function
# http://stackoverflow.com/questions/14154756/how-to-extract-dependencies-from-a-pypi-package

import os, sys, distutils, setuptools, re
try:
	from StringIO import StringIO
except ImportError:
	from io import StringIO

setup_file = os.path.abspath('setup.py')

# fakes
_real_stdout = sys.stdout
sys.stdout = StringIO()
__file__ = setup_file
sys.path.insert(0, os.getcwd()) # for crazy packages that import themselves during setup
sys.argv = [setup_file, '--dry-run'] # try and stop setuptools from being so mental
with open(setup_file) as f:
	d = f.read()
	d = re.sub(r'setup_requires\s*=[_a-zA-Z]+,', '', d) # Hackiest of hacks

try:
	exec(d, globals(), globals())
except SystemExit:
	pass
import json
info = distutils.core._setup_distribution

if os.environ.get('VERBOSE', '0' == '1'):
	print(repr(info.__dict__), file=sys.stderr)

scripts = info.scripts
if scripts:
	#XXX should we append .exe to script names on windows here?
	scripts = [{"path":script, "name": os.path.splitext(os.path.basename(script))[0]} for script in scripts ]
else:
	scripts = []
	try:
		# maybe they're using setuptools scripts...
		entry_points = info.entry_points['console_scripts']
		#XXX what about gui scripts?
	except (AttributeError, KeyError, TypeError) as e:
		pass
	else:
		for entry in entry_points:
			name, modulepath = list(map(lambda s:s.strip(), entry.split('=', 1)))
			parts = modulepath.split(':')
			script = {'name':name}
			assert parts and parts[0], entry
			script['module'] = parts[0]
			if len(parts) > 1:
				assert len(parts) <= 2, "multi-level entry point: %s // %r" % (entry,parts)
				script['fn'] = parts[1]
			scripts.append(script)

def process_extras_requires(req):
	# make sure requirements are a list (sometimes it's a string for single dependencies)
	for key,val in req.items():
		if not isinstance(val, list):
			req[key] = [val]
	return req

info = {
	'install_requires': getattr(info, 'install_requires', None) or [],
	'extras_requires': process_extras_requires(getattr(info, 'extras_require', None) or {}),
	'use_2to3': getattr(info, 'use_2to3', None),
	'commands': info.commands,
	'scripts': scripts,
	'packages': info.packages,
	'namespace_packages': getattr(info, 'namespace_packages', []),
	'has_c_libraries': info.has_c_libraries(),
	'has_ext_modules': info.has_ext_modules(),
}
json.dump(info, _real_stdout)
