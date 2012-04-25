import tempfile
import shutil
import os

from zeroinstall.zerostore import manifest, unpack

class Archive(object):
	def __init__(self, url, type=None, extract=None, local_file=None):
		self.url = url
		base = tempfile.mkdtemp()
		try:
			filename = url.rsplit('/', 1)[1]
			assert filename or local_file
			dest='extract'
			fetch(url, base=base, filename=filename, dest=dest, type=type)
			if local_file is None:
				local_file = os.path.join(base, filename)
			self.manifest = get_manifest(os.path.join(base, dest), extract=extract)
			self.size = os.stat(local_file).st_size
		finally:
			shutil.rmtree(base)

def fetch(url, base, filename, dest, extract=None, type=None, local_file=None):
	with open(local_file or os.path.join(base, filename), 'rw') as data:
		if local_file is None:
			with urllib2.urlopen(url) as stream:
				while true:
					chunk = stream.read(1024)
					if not chunk: break
					data.write(chunk)
		data.seek(0)
		unpack.unpack_archive(url, data = data, destdir = os.path.join(base, dest), extract=extract, type=type)

def get_manifest(root, extract, algname='sha256'):
	if extract is not None:
		root = os.path.join(root, extract)
	try:
		alg = manifest.algorithms.get(algname)
	except KeyError:
		raise ValueError("unknown algorithm: %s" % (algname,))
	digest = alg.new_digest()
	for line in alg.generate_manifest(root):
		digest.update(line + '\n')
	return (alg, alg.getID(digest))


