import sys
from mocktest import *
from zeroinstall_downstream import pypi

mandy = pypi.Pypi('mandy')
class PypiTest(TestCase):
	def test_initial_info(self):
		self.assertEqual(mandy.homepage, 'http://pypi.python.org/pypi/mandy/')
		self.assertEqual(mandy.upstream_id, 'mandy')
		self.assertEqual(mandy.upstream_type, 'pypi')
		self.assertEqual(mandy.latest_version, '0.1.4')
		self.assertEqual(mandy.summary, 'a terse command-line options parser')
		self.assertMatches(string_containing('mandy" is a simple com(mand)-line option parser (see the tenuous name link there?)'), mandy.description)

	def test_update_check(self):
		self.assertTrue(mandy.updated_since('0.1.3'))
		self.assertFalse(mandy.updated_since('0.1.4'))
		self.assertFalse(mandy.updated_since('0.2'))

	def test_implementation_info(self):
		impl = mandy.latest_release
		self.assertEqual(impl.version, '0.1.4')
		self.assertEqual(impl.url, 'http://pypi.python.org/packages/source/m/mandy/mandy-0.1.4.tar.gz')
		self.assertEqual(impl.released, '2009-06-24')
