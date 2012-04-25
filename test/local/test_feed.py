from StringIO import StringIO

from mocktest import *
from BeautifulSoup import BeautifulStoneSoup as ParseXML

from zeroinstall_downstream.feed import Feed
from zeroinstall_downstream.project import SOURCES

def dumpxml(xml):
	xml = str(xml)
	import pygments
	from pygments.lexers import get_lexer_by_name
	from pygments.formatters import TerminalFormatter
	return pygments.highlight(xml, get_lexer_by_name('xml'), TerminalFormatter())

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

		self.proj2 = mock('project2').with_children(
			homepage='http://example.com/project2',
			upstream_id='upstream_id2',
			upstream_type='upstream_mock2',
			latest_version='2.5.12',
			summary='the BEST project2',
			description='use it for all your projecty needs!2',
			latest_release=mock('latest release2').with_children(
				version='2.5.12',
				url='http://example.com/download-2.5.12',
				released='2012-01-012'
			)
		).with_methods(
			updated_since = lambda v: v != '2.5.12'
		)
		self.clear_buffer()
	
	def clear_buffer(self):
		self.buffer = StringIO()
	
	def saved_dom(self):
		xml = self.buffer.getvalue()
		return ParseXML(xml).interface

	def write_initial_feed(self, proj):
		feed = Feed.from_project(proj, 'http://example.com/')
		feed.save(self.buffer)
		self.buffer.seek(0)
	
	def assert_details_match(self, project):
		saved_dom = self.saved_dom()
		self.assertEqual(saved_dom.find('homepage').text, project.homepage)
		self.assertEqual(saved_dom.find('summary').text, project.summary)
		self.assertEqual(saved_dom.find('description').text, project.description)
		upstream_attrs = dict(saved_dom.find('gfxmonk:upstream').attrs)
		self.assertEqual(upstream_attrs, {'type': project.upstream_type, 'id': project.upstream_id})
		self.assertNotEqual(saved_dom.find('group'), None)

	def test_feed_creation(self):
		feed = Feed.from_project(self.proj, "http://example.com/my-project.xml")
		feed.save(self.buffer)
		output = self.saved_dom()
		self.assertEqual(output['uri'], 'http://example.com/my-project.xml')
		self.assert_details_match(self.proj)
		self.assertEqual(output.find('name').text, 'my-project')
	
	def test_update_details(self):
		self.write_initial_feed(self.proj)
		class UpstreamMock(object):
			def __new__(cls, id):
				assert id == 'upstream_id'
				# return a project with _new_ details
				return self.proj2
		modify(SOURCES)['upstream_mock'] = UpstreamMock
		feed = Feed.from_file(self.buffer)
		self.assertEqual(feed.project, self.proj2)

		feed.update_metadata()
		self.clear_buffer()
		feed.save(self.buffer)
		self.assert_details_match(self.proj2)
	
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
	def test_constructing_with_arbitrary_attributes(self):
		pass
