import sys
from mocktest import *
from zeroinstall_downstream.project import rubygems
from zeroinstall_downstream.composite_version import CompositeVersion

project = rubygems.Rubygems('xargs')
class RubyTest(TestCase):
	def test_project_homepage(self):
		self.assertEqual(project.homepage, 'http://rubygems.org/gems/xargs')
		self.assertEqual(project.url, 'https://rubygems.org/gems/xargs')
	def test_project_id(self):
		self.assertEqual(project.id, 'xargs')
	def test_project_type(self):
		self.assertEqual(project.upstream_type, 'rubygems')
	def test_project_latest_version(self):
		self.assertEqual(project.latest_version, CompositeVersion('0.0.1'))
	def test_project_summary(self):
		self.assertEqual(project.summary, "xargs ruby gem")
	def test_project_description(self):
		self.assertEqual(project.description, "Module to emulate the 'xargs' utility from a unix system")

	def test_implementation_info(self):
		impl = project.latest_release
		self.assertEqual(impl.version, CompositeVersion('0.0.1'))
		self.assertEqual(impl.url, 'http://rubygems.org/gems/xargs-0.0.1.gem')
		self.assertEqual(impl.archive_type, 'application/x-ruby-gem')
		self.assertEqual(impl.released, '2006-04-09')

	def test_specific_version_implementation_info(self):
		# should probably find a dead project with multiple versions, but oh well
		impl = project.implementation_for(CompositeVersion('0.0.1'))
		self.assertEqual(impl.version, CompositeVersion('0.0.1'))
		self.assertEqual(impl.url, 'http://rubygems.org/gems/xargs-0.0.1.gem')
		self.assertEqual(impl.archive_type, 'application/x-ruby-gem')
		self.assertEqual(impl.released, '2006-04-09')
	
	def test_derived_version_strings(self):
		project = rubygems.Rubygems('ghost')

		# version string uses literal upstream version
		impl = project.implementation_for(CompositeVersion('1.0.0.pre.2'))

		# implementation uses parsed version
		self.assertEqual(str(impl.version.derived), '1.0.0-pre-2')
