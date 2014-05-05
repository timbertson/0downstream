import os
from mocktest import *
import requests

from zeroinstall_downstream.archive import Archive
from .util import *

mandy = os.path.join(os.path.dirname(__file__), 'fixtures', 'mandy-0.1.4.tar.gz')
mandy_extracted = os.path.join(os.path.dirname(__file__), 'fixtures', 'mandy-extracted.tar.gz')

def manifests(archive):
	tag = archive._digest_tag()
	return {
		'sha256': tag['sha256']
	}

class MockDownloadedArchiveTest(TestCase):
	def setUp(self):
		self.data = None
		when(requests).get.then_call(self.get_data)
	
	def get_data(self, *a, **k):
		assert self.data, "use_archive() not called yet"
		return self.data

	def tearDown(self):
		if self.data is not None:
			self.data.raw.close()
	
	def use_archive(self, path):
		self.data = mock('http stream').with_children(raw=open(path)).with_methods(raise_for_status=None)

	def test_basic_archive_download_and_manifest(self):
		self.use_archive(mandy)
		with Archive(url='http://example.com/mandy.tar.gz') as archive:
			self.assertEqual(archive.url, 'http://example.com/mandy.tar.gz')
			self.assertEqual(archive.extract, 'mandy-0.1.4')
			self.assertEqual(archive.size, 6795)
			self.assertEqual(manifests(archive), {'sha256':'6f1d3c8ed295c16dc9a4eae37587f5cd38c875aa37489f0db7eef212589505ca'})

	def test_archive_doesnt_guess_or_use_extract_when_None_is_given(self):
		self.use_archive(mandy)
		with Archive(url='http://example.com/mandy.tar.gz', extract=None) as archive:
			self.assertEqual(archive.url, 'http://example.com/mandy.tar.gz')
			self.assertEqual(archive.size, 6795)
			self.assertEqual(archive.extract, None)
			self.assertEqual(manifests(archive), {'sha256':'b7eb422cf2eab00eb7b2ab925ff4ea5c0155c3b39757809bcd34a3283c44e85a'})

	def test_archive_will_have_no_extract_when_multiple_files_present(self):
		self.use_archive(mandy_extracted)
		with Archive(url='http://example.com/mandy.tar.gz') as archive:
			self.assertEqual(archive.size, 6794)
			self.assertEqual(archive.extract, None)
			self.assertEqual(manifests(archive), {'sha256':'6f1d3c8ed295c16dc9a4eae37587f5cd38c875aa37489f0db7eef212589505ca'})

	def test_archive_will_use_supplied_extract(self):
		self.use_archive(mandy_extracted)
		with Archive(url='http://example.com/mandy.tar.gz', extract='mandy.egg-info') as archive:
			self.assertEqual(manifests(archive), {'sha256':'4aa6aacde9dfcdd7c1a7c6fa76a7d244250cb17aacd96b674ce79fbdf1444577'})
			self.assertEqual(archive.size, 6794)
			self.assertEqual(archive.extract, 'mandy.egg-info')



