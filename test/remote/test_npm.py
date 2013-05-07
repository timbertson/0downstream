import sys
from mocktest import *
from zeroinstall_downstream.project import npm
from zeroinstall_downstream.composite_version import CompositeVersion

project = npm.Npm('jejune')
class NpmTest(TestCase):
	def test_project_homepage(self):
		self.assertEqual(project.homepage, 'https://npmjs.org/package/jejune')
		self.assertEqual(project.url, 'https://npmjs.org/package/jejune')
	def test_project_id(self):
		self.assertEqual(project.id, 'jejune')
	def test_project_type(self):
		self.assertEqual(project.upstream_type, 'npm')
	def test_project_latest_version(self):
		self.assertEqual(project.latest_version, CompositeVersion('0.1.1'))
	def test_project_summary(self):
		self.assertEqual(project.summary, 'jejune npm package')
	def test_project_description(self):
		self.assertEqual(project.description, 'Generating stereotypical usernames has never been easier')

	def test_implementation_info(self):
		impl = project.latest_release
		self.assertEqual(impl.version, CompositeVersion('0.1.1'))
		self.assertEqual(impl.url, 'http://registry.npmjs.org/jejune/-/jejune-0.1.1.tgz')
		self.assertEqual(impl.released, '2013-01-10')

	def test_old_implementation_info(self):
		impl = project.implementation_for(CompositeVersion('0.1.0'))
		self.assertEqual(impl.version, CompositeVersion('0.1.0'))
		self.assertEqual(impl.url, 'http://registry.npmjs.org/jejune/-/jejune-0.1.0.tgz')
		self.assertEqual(impl.released, '2013-01-10')
