from __future__ import print_function
# http://stackoverflow.com/questions/14154756/how-to-extract-dependencies-from-a-pypi-package

#XXX depend on setuptools, distribute is dead

import os, sys, distutils
setup_file = os.path.abspath('setup.py')
__file__ = setup_file
sys.path.insert(0, os.getcwd()) # for crazy packages that import themselves during setup
with open(setup_file) as f:
	d = f.read()
try:
	exec(d, globals(), globals())
except SystemExit:
	pass
import json
info = distutils.core._setup_distribution

# print(repr(info.__dict__), file=sys.stderr)

scripts = info.scripts
if scripts:
	#XXX should we append .exe to script names on windows here?
	scripts = [{"path":script, "name": os.path.splitext(os.path.basename(script))} for script in scripts ]
else:
	scripts = []
	try:
		# maybe they're using setuptools scripts...
		entry_points = info.entry_points['console_scripts']
		#XXX what about gui scripts?
	except (AttributeError, KeyError) as e:
		pass
	else:
		#XXX do scripts always end up in "bin"? Probably...
		for entry in entry_points:
			name, modulepath = list(map(lambda s:s.strip(), entry.split('=', 1)))
			parts = modulepath.split(':')
			script = {'name':parts[0]}
			assert parts and parts[0], entry
			script['module'] = parts[0]
			if len(parts) > 1:
				assert len(parts) <= 2, "multi-level entry point: %s // %r" % (entry,parts)
				script['fn'] = parts[1]
			scripts.append(script)

info = {
	'install_requires': getattr(info, 'install_requires', None) or [],
	'use_2to3': getattr(info, 'use_2to3', None),
	'commands': info.commands,
	'scripts': scripts,
	'packages': info.packages,
	'has_c_libraries': info.has_c_libraries(),
	'has_ext_modules': info.has_ext_modules(),
}
json.dump(info, sys.stdout)
