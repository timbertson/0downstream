import sys
from mocktest import *
from zeroinstall_downstream.project import github

project = github.Github('gfxmonk/pagefeed-android')
class GithubTest(TestCase):
	def test_project_homepage(self):
		self.assertEqual(project.homepage, 'https://github.com/gfxmonk/pagefeed-android')
	def test_project_id(self):
		self.assertEqual(project.upstream_id, 'gfxmonk/pagefeed-android')
	def test_project_type(self):
		self.assertEqual(project.upstream_type, 'github')
	def test_project_latest_version(self):
		self.assertEqual(project.latest_version, '0.3')
	def test_project_summary(self):
		self.assertEqual(project.summary, 'android app for pagefeed.appspot.com')

	def test_project_description(self):
		self.assertEqual(project.description, 'android app for pagefeed.appspot.com')

	def test_update_check(self):
		self.assertTrue(project.updated_since('0.1.3'))
		self.assertFalse(project.updated_since('0.3'))
		self.assertFalse(project.updated_since('0.5'))

	def test_implementation_version(self):
		self.assertEqual(project.latest_release.version, '0.3')
	def test_implementation_url(self):
		self.assertEqual(project.latest_release.url, 'https://github.com/gfxmonk/pagefeed-android/tarball/0.3')
	def test_implementation_type(self):
		self.assertEqual(project.latest_release.archive_type, 'application/x-compressed-tar')
	def test_implementation_releasedate(self):
		self.assertEqual(project.latest_release.released, '2011-03-07')