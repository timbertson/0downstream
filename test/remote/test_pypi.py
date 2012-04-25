import sys
from mocktest import *
from zeroinstall_downstream.project import pypi

project = pypi.Pypi('mandy')
class PypiTest(TestCase):
	def test_project_homepage(self):
		self.assertEqual(project.homepage, 'http://pypi.python.org/pypi/mandy/')
	def test_project_id(self):
		self.assertEqual(project.upstream_id, 'mandy')
	def test_project_type(self):
		self.assertEqual(project.upstream_type, 'pypi')
	def test_project_latest_version(self):
		self.assertEqual(project.latest_version, '0.1.4')
	def test_project_summary(self):
		self.assertEqual(project.summary, 'a terse command-line options parser')
	def test_project_description(self):
		self.assertMatches(string_containing('mandy" is a simple com(mand)-line option parser (see the tenuous name link there?)'), project.description)

	def test_update_check(self):
		self.assertTrue(project.updated_since('0.1.3'))
		self.assertFalse(project.updated_since('0.1.4'))
		self.assertFalse(project.updated_since('0.2'))

	def test_implementation_info(self):
		impl = project.latest_release
		self.assertEqual(impl.version, '0.1.4')
		self.assertEqual(impl.url, 'http://pypi.python.org/packages/source/m/mandy/mandy-0.1.4.tar.gz')
		self.assertEqual(impl.released, '2009-06-24')
