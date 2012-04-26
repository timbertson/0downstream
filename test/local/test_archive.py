import os
from mocktest import *

from zeroinstall_downstream.archive import Archive, urllib2

mandy = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'mandy-0.1.4.tar.gz')
mandy_extracted = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'mandy-extracted.tar.gz')

class MockDownloadedArchiveTest(TestCase):
	def setUp(self):
		self.data = None
		when(urllib2).urlopen.then_call(self.get_data)
	
	def get_data(self, *a):
		if self.data is None:
			self.data = open(mandy)
		return self.data

	def tearDown(self):
		if self.data is not None:
			self.data.close()

	def test_basic_archive_download_and_manifest(self):
		archive = Archive(url='http://example.com/mandy.tar.gz')
		self.assertEqual(archive.url, 'http://example.com/mandy.tar.gz')
		self.assertEqual(archive.manifests, {'sha1new':'887dab86294802388fa1382c268185afff7c47a8', 'sha256':'6f1d3c8ed295c16dc9a4eae37587f5cd38c875aa37489f0db7eef212589505ca'})
		self.assertEqual(archive.size, 6795)
		self.assertEqual(archive.extract, 'mandy-0.1.4')

class LocalArchiveTest(TestCase):
	def test_archive_will_use_local_file(self):
		expect(urllib2).urlopen.never()
		archive = Archive(url='http://example.com/mandy.tar.gz', local_file = mandy)
		self.assertEqual(archive.url, 'http://example.com/mandy.tar.gz')
		self.assertEqual(archive.manifests, {'sha1new':'887dab86294802388fa1382c268185afff7c47a8', 'sha256':'6f1d3c8ed295c16dc9a4eae37587f5cd38c875aa37489f0db7eef212589505ca'})
		self.assertEqual(archive.size, 6795)
		self.assertEqual(archive.extract, 'mandy-0.1.4')

	def test_archive_doesnt_guess_or_use_extract_when_false_is_given(self):
		archive = Archive(url='http://example.com/mandy.tar.gz', local_file = mandy, extract=False)
		self.assertEqual(archive.url, 'http://example.com/mandy.tar.gz')
		self.assertEqual(archive.manifests, {'sha1new':'55388d828dff5ed41dcad47308e2773b30971380', 'sha256':'b7eb422cf2eab00eb7b2ab925ff4ea5c0155c3b39757809bcd34a3283c44e85a'})
		self.assertEqual(archive.size, 6795)
		self.assertEqual(archive.extract, None)

	def test_archive_will_have_no_extract_when_multiple_files_present(self):
		archive = Archive(url='http://example.com/mandy.tar.gz', local_file = mandy_extracted)
		self.assertEqual(archive.manifests, {'sha1new':'887dab86294802388fa1382c268185afff7c47a8', 'sha256':'6f1d3c8ed295c16dc9a4eae37587f5cd38c875aa37489f0db7eef212589505ca'})
		self.assertEqual(archive.size, 6794)
		self.assertEqual(archive.extract, None)

	def test_archive_will_use_supplied_extract(self):
		expect(urllib2).urlopen.never()
		archive = Archive(url='http://example.com/mandy.tar.gz', local_file = mandy_extracted, extract='mandy.egg-info')
		self.assertEqual(archive.manifests, {'sha1new':'813d2b89d98d8ac693a67297f4834ba13af04120', 'sha256':'4aa6aacde9dfcdd7c1a7c6fa76a7d244250cb17aacd96b674ce79fbdf1444577'})
		self.assertEqual(archive.size, 6794)
		self.assertEqual(archive.extract, 'mandy.egg-info')



