import sys
from mocktest import *
from zeroinstall_downstream.project import guess_project_info

class ParsePypiTest(TestCase):
	def test_parse_pypi(self):
		info = guess_project_info('http://pypi.python.org/pypi/mocktest/0.1')
		self.assertEqual(info, {'type':'pypi','id':'mocktest'})

		info = guess_project_info('http://pypi.python.org/pypi/mocktest/0.1')
		self.assertEqual(info, {'type':'pypi','id':'mocktest'})

	def test_parse_github(self):
		info = guess_project_info('https://github.com/gfxmonk/pagefeed-android/blah')
		self.assertEqual(info, {'type':'github','id':'gfxmonk/pagefeed-android'})

		info = guess_project_info('https://github.com/gfxmonk/pagefeed-android')
		self.assertEqual(info, {'type':'github','id':'gfxmonk/pagefeed-android'})

	def test_parse_fail(self):
		self.assertRaises(ValueError, lambda: guess_project_info('http://gfxmonk.net/whatever'))
