#!usr/bin/env python
from __future__ import print_function
import os, sys, optparse, shutil
def mkdirp(p):
	if not os.path.exists(p):
		os.makedirs(p)

old_path, new_path, src, dest = sys.argv[1:]
print("Installing into %s" % (dest,))

with open(old_path) as f:
	old = set([line.strip() for line in f.readlines()])

with open(new_path) as f:
	for line in f:
		line = line.strip()
		assert not os.path.isabs(line), "Absolute path: %s" %(line,)
		if line in old:
			continue
		full_src = os.path.join(src, line)
		full_dest = os.path.join(dest, line)
		mkdirp(os.path.dirname(full_dest))
		print(" - %s" % (line,))
		shutil.copy2(full_src, full_dest)

