#!/usr/bin/env python
from __future__ import print_function
import os
import sys
import collections
import shutil
import subprocess

def mkdirp(p):
	if not os.path.exists(p): os.makedirs(p)

def create_local_repo(repo_path, src_paths):
	print("Creating opam package repo in %s" % (os.path.abspath(repo_path),))
	mkdirp(repo_path)
	packages = {}
	seen_paths = set()
	seen_ids = set()

	for path in src_paths:
		if not path.strip():
			# skip empty path
			continue

		if path in seen_paths:
			# skip duplicate locations
			continue

		seen_paths.add(path)

		for id in os.listdir(path):
			fp = os.path.join(path, id)
			if not os.path.isdir(fp):
				print("Not a directory: %s" % (fp,))
				continue

			if id in seen_ids:
				print("Package already added - skipping %s" % (fp,))
				continue
			seen_ids.add(id)
			
			print("Adding %s" % (id,))
			name, _version = id.split('.', 1)

			dest_root = os.path.join(repo_path, 'packages', name)
			mkdirp(dest_root)
			sources_root = os.path.join(repo_path, 'sources', name)
			mkdirp(sources_root)

			# os.symlink(fp, os.path.join(dest_root, id))

			# XXX if we want to replace specific files:
			dest_root = os.path.join(dest_root, id)
			mkdirp(dest_root)

			for meta in os.listdir(fp):
				full_meta = os.path.join(fp, meta)
				# Hacky: we look for a `src` file with a relative path, and
				# convert that into an abspathed `url` definition
				# (since opam needs absolute paths, but we don't want to distribute those)
				if meta == 'url':
					print("WARN: ignoring upstream `url` file: %s" % (full_meta,))
					continue
				elif meta == 'src':
					with open(full_meta) as f:
						src_rel_path = f.read().strip()

					meta = 'url'
					with open(os.path.join(dest_root, meta), 'w') as f:
						src_abs = os.path.abspath(os.path.join(fp, src_rel_path))
						assert os.path.exists(src_abs), "src_abs does not exist: %s" %(src_abs,)

						# 0install sources are readonly, but opam wants to
						# write stuff into them. So let's make a writeable copy.

						# XXX we should just fix opam to use --chmod=u+w or something
						# when it does a local rsync
						copied_src = os.path.join(sources_root, id)
						subprocess.check_call(['cp', '-a', src_abs, copied_src])
						subprocess.check_call(['chmod', '-R', 'u+w', copied_src])

						# XXX escape special characters
						f.write('local: "%s"' % (copied_src,))
					continue

				print("Copying %s" % (full_meta,))
				if os.path.isdir(full_meta):
					os.symlink(full_meta, os.path.join(dest_root, meta))
				else:
					shutil.copyfile(full_meta, os.path.join(dest_root, meta))

if __name__ == '__main__':
	import optparse
	p = optparse.OptionParser('usage: %prog [OPTIONS] repo_path')
	opts, args = p.parse_args()
	assert len(args) == 1, p.format_help()

	repo_path, = args
	sources = set(os.environ['OPAM_PKG_PATH'].split(os.pathsep))
	create_local_repo(repo_path, sources)


