import StringIO

from mocktest import *
from BeautifulSoup import BeautifulStoneSoup as ParseXML

from zeroinstall_downstream.feed import Feed

class TestFeed(TestCase):
	def setUp(self):
		self.proj = mock('project').with_children(
			homepage='http://example.com/project',
			upstream_id='upstream_id',
			upstream_type='upstream_mock',
			latest_version='2.5.1',
			summary='the BEST project',
			description='use it for all your projecty needs!',
			latest_release=mock('latest release').with_children(
				version='2.5.1',
				url='http://example.com/download-2.5.1',
				released='2012-01-01'
			)
		).with_methods(
			updated_since = lambda v: v != '2.5.1'
		)
		self.feed_file = StringIO.StringIO()
	
	@property
	def saved_feed(self):
		print self.feed_file.getvalue()
		return ParseXML(self.feed_file.getvalue()).interface
	
	def assert_details_match(self, output, project):
		self.assertEqual(output.find('homepage').text, project.homepage)
		self.assertEqual(output.find('summary').text, project.summary)
		self.assertEqual(output.find('description').text, project.description)
		upstream_attrs = dict(output.find('gfxmonk:upstream').attrs)
		self.assertEqual(upstream_attrs, {'type': project.upstream_type, 'id': project.upstream_id})
		self.assertNotEqual(output.find('group'), None)


	def test_feed_creation(self):
		feed = Feed.from_project(self.proj, "http://example.com/my-project.xml")
		feed.save(self.feed_file)
		output = self.saved_feed
		self.assertEqual(output['uri'], 'http://example.com/my-project.xml')
		self.assert_details_match(output, self.proj)
		self.assertEqual(output.find('name').text, 'my-project')
	
	def test_add_implementation_and_update_details(self):
		pass
	def test_add_implementation_without_modifying_details(self):
		pass
	def test_add_initial_implementation_to_source_group(self):
		pass
	def test_add_implementation_to_source_group(self):
		pass
	def test_checking_for_new_release(self):
		pass

class TestFeedProcessing(TestCase):
	def test_constructing_pypi_project_from_feed(self):
		pass
	def test_constructing_github_project_from_feed(self):
		pass
