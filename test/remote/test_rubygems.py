import sys
from mocktest import *
from zeroinstall_downstream.project import rubygems

project = rubygems.Rubygems('xargs')
class RubyTest(TestCase):
	def test_project_homepage(self):
		self.assertEqual(project.homepage, 'http://rubygems.org/gems/xargs')
	def test_project_id(self):
		self.assertEqual(project.upstream_id, 'xargs')
	def test_project_type(self):
		self.assertEqual(project.upstream_type, 'rubygems')
	def test_project_latest_version(self):
		self.assertEqual(project.latest_version, '0.0.1')
	def test_project_summary(self):
		self.assertEqual(project.summary, "xargs ruby gem")
	def test_project_description(self):
		self.assertEqual(project.description, "Module to emulate the 'xargs' utility from a unix system")

	def test_update_check(self):
		self.assertTrue(project.updated_since('0.0.0'))
		self.assertFalse(project.updated_since('0.1'))

	def test_implementation_info(self):
		impl = project.latest_release
		self.assertEqual(impl.version, '0.0.1')
		self.assertEqual(impl.url, 'http://rubygems.org/gems/xargs-0.0.1.gem')
		self.assertEqual(impl.archive_type, 'application/x-ruby-gem')
		self.assertEqual(impl.released, '2006-04-09')
