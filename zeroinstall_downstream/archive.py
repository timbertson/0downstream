import tempfile
import shutil
import os
import urllib2

from zeroinstall.zerostore import manifest, unpack
import contextlib

import logging
log = logging.getLogger(__name__)

class Archive(object):
	def __init__(self, url, type=None, extract=None, local_file=None):
		self.url = url
		base = tempfile.mkdtemp()
		try:
			filename = url.rsplit('/', 1)[1]
			assert filename or local_file
			dest='root'
			fetch(url, base=base, filename=filename, dest=dest, type=type, local_file=local_file)
			if extract is None:
				files_extracted = os.listdir(os.path.join(base, dest))
				log.debug("found %s files in archive" % len(files_extracted))
				if len(files_extracted) == 1 and extract is None:
					extract = files_extracted[0]
			if extract is False:
				extract = None
			log.debug("extract = %s" % (extract,))

			def list_toplevel():
				toplevel_path = os.path.join(base, dest)
				if extract is not None:
					toplevel_path = os.path.join(toplevel_path, extract)
				contents = os.listdir(toplevel_path)
				sep = "\n  "
				print "NOTE: Toplevel contents or archive are:", sep.join(sorted(contents))
			list_toplevel()

			self.extract = extract
			self.manifests = {}
			self.manifests['sha1new'] = get_manifest(os.path.join(base, dest), extract=extract, algname='sha1new')
			log.debug("sha1new manifest = %s" % (self.manifests['sha1new'],))
			self.manifests['sha256']  = get_manifest(os.path.join(base, dest), extract=extract, algname='sha256')
			log.debug("sha256 manifest = %s" % (self.manifests['sha256'],))
			self.type = type
			if local_file is None:
				local_file = os.path.join(base, filename)
			self.size = os.stat(local_file).st_size
		finally:
			if log.isEnabledFor(logging.DEBUG):
				log.debug("debug mode enabled - NOT cleaning up directory: %s" % (base,))
			else:
				shutil.rmtree(base)

def fetch(url, base, filename, dest, extract=None, type=None, local_file=None):
	mode = 'w+' if local_file is None else 'r'
	with open(local_file or os.path.join(base, filename), mode) as data:
		if local_file is None:
			log.info("downloading %s -> %s" % (url, os.path.join(base, filename)))
			with contextlib.closing(urllib2.urlopen(url)) as stream:
				while True:
					chunk = stream.read(1024)
					if not chunk: break
					data.write(chunk)
			data.seek(0)
		os.makedirs(os.path.join(base, dest))
		unpack.unpack_archive(url, data = data, destdir = os.path.join(base, dest), extract=extract, type=type)

def get_manifest(root, extract, algname='sha256'):
	if extract is not None:
		root = os.path.join(root, extract)
	try:
		alg = manifest.algorithms.get(algname)
		log.debug("got algorithm for %s: %r" % (algname, alg,))
	except KeyError:
		raise ValueError("unknown algorithm: %s" % (algname,))
	digest = alg.new_digest()
	for line in alg.generate_manifest(root):
		digest.update(line + '\n')
	return digest.hexdigest()


