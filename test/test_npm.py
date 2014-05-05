from .util import *
from zeroinstall_downstream.project import npm
from zeroinstall_downstream.composite_version import CompositeVersion
from zeroinstall_downstream.api import FeedLocation, Tag

def resolve_url(project):
	return FeedLocation(path=None, url='#%s' % project.id)

def requirement(url, min=None, max=None):
	version_attrs = {}
	if min is not None: version_attrs['not-before'] = min
	if max is not None: version_attrs['before'] = max
	return Tag('requires', {'interface':url}, [Tag('version', version_attrs)])

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

	def test_release_info(self):
		impl = project.latest_release
		self.assertEqual(impl.version, CompositeVersion('0.1.1'))
		self.assertEqual(impl.url, 'http://registry.npmjs.org/jejune/-/jejune-0.1.1.tgz')
		self.assertEqual(impl.released, '2013-01-10')

	def test_specific_release_info(self):
		project = npm.Npm('block-stream')
		impl = project.get_release(CompositeVersion('0.0.7'))
		self.assertEqual(impl.version, CompositeVersion('0.0.7'))

		with impl:
			impl.detect_dependencies(resolve_url)
			self.assertEqual(impl.runtime_dependencies, [requirement('#inherits', '2.0.0', '2.1')])
			self.assertEqual(impl.compile_dependencies, [requirement('#inherits', '2.0.0', '2.1'), requirement('#tap', '0', '1')])
