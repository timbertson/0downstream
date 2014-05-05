import sys
from mocktest import *
from zeroinstall_downstream.project import pypi
from zeroinstall_downstream.composite_version import CompositeVersion

project = pypi.Pypi('mandy')
class PypiTest(TestCase):
	def test_project_homepage(self):
		self.assertEqual(project.homepage, 'http://pypi.python.org/pypi/mandy/')
		self.assertEqual(project.url, 'http://pypi.python.org/pypi/mandy')
	def test_project_id(self):
		self.assertEqual(project.id, 'mandy')
	def test_project_type(self):
		self.assertEqual(project.upstream_type, 'pypi')
	def test_project_latest_version(self):
		self.assertEqual(project.latest_version, CompositeVersion('0.1.4'))
	def test_project_summary(self):
		self.assertEqual(project.summary, 'a terse command-line options parser')
	def test_project_description(self):
		self.assertMatches(string_containing('mandy" is a simple com(mand)-line option parser (see the tenuous name link there?)'), project.description)

	def test_implementation_info(self):
		impl = project.latest_release
		self.assertEqual(impl.version, CompositeVersion('0.1.4'))
		self.assertEqual(impl.url, 'http://pypi.python.org/packages/source/m/mandy/mandy-0.1.4.tar.gz')
		self.assertEqual(impl.released, '2009-06-24')

	def test_old_implementation_info(self):
		impl = project.implementation_for(CompositeVersion('0.1.3'))
		self.assertEqual(impl.version, CompositeVersion('0.1.3'))
		self.assertEqual(impl.url, 'http://pypi.python.org/packages/source/m/mandy/mandy-0.1.3.tar.gz')
		self.assertEqual(impl.released, '2009-06-24')
