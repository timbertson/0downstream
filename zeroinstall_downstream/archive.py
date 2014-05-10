import tempfile
import shutil
import os
import re

from zeroinstall.zerostore import manifest, unpack
import contextlib

from .tag import Tag

import logging
log = logging.getLogger(__name__)

_sentinel = object()

class Archive(object):
	def __init__(self, url, extract=_sentinel, type=None):
		self.url = url
		self.recipe_steps = []
		self.extract = extract
		self.type = type
		self.id = url

	def _archive_tag(self):
		return Tag("archive", {"href": self.url, "size": str(self.size), 'extract': self.extract or ''})

	def _digest_tag(self):
		sha1new = get_manifest(self.local, extract=self.extract, algname='sha1new')
		self.id = "sha1new=%s" % (sha1new,)
		sha256 = get_manifest(self.local, extract=self.extract, algname='sha256')
		return Tag('manifest-digest', {"sha256":sha256})

	def add_to(self, impl, doc):
		archive = self._archive_tag()
		fetch = archive
		if self.recipe_steps:
			recipe = Tag('recipe', children=[archive] + self.recipe_steps)
			fetch = recipe

		fetch.addTo(impl, doc)
		self._digest_tag().addTo(impl, doc)
	
	def rename(self, source, dest):
		local_source = os.path.join(self.local, source)
		local_dest = os.path.join(self.local, dest)
		os.rename(local_source, local_dest)
		self.recipe_steps.append(Tag('rename', {'source': source, 'dest':dest}))

	def __enter__(self):
		self.local = tempfile.mkdtemp()
		try:
			self.size = fetch(self.url, base=self.local, type=self.type)

			# emulate 0publish behaviour when no extact is specified
			if self.extract is _sentinel:
				self.extract = None
				files_extracted = os.listdir(self.local)
				log.debug("found %s files in archive" % len(files_extracted))
				if len(files_extracted) == 1:
					self.extract = files_extracted[0]
			log.debug("extract = %s" % (self.extract,))

		except:
			self._cleanup()
			raise
		return self
	
	def _cleanup(self):
		if not hasattr(self, 'local'): return
		shutil.rmtree(self.local)
		del self.local

	def __exit__(self, exc_type, exc_val, tb):
		self._cleanup()

def fetch(url, base, type=None):
	'''returns the filesize of the downloaded file'''
	import requests
	import contextlib
	import shutil
	with contextlib.closing(tempfile.TemporaryFile()) as f:
		req = requests.get(url, stream=True)
		req.raise_for_status()
		shutil.copyfileobj(req.raw, f)
		f.seek(0)
		unpack.unpack_archive(url, data = f, destdir = base, type=type)
		return os.fstat(f.fileno()).st_size

def get_manifest(root, extract, algname='sha256'):
	if extract:
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


