from StringIO import StringIO

from mocktest import *
from BeautifulSoup import BeautifulStoneSoup as ParseXML

from zeroinstall_downstream.feed import Feed
import zeroinstall_downstream.feed as feed_module
from zeroinstall_downstream.project import SOURCES
from zeroinstall_downstream import archive
from zeroinstall_downstream.composite_version import CompositeVersion

def dumpxml(xml):
	xml = str(xml)
	import pygments
	from pygments.lexers import get_lexer_by_name
	from pygments.formatters import TerminalFormatter
	return pygments.highlight(xml, get_lexer_by_name('xml'), TerminalFormatter())

class TestFeed(TestCase):
	def setUp(self):
		def mkarchive(*a, **k):
			m = mock('archive').with_children(size=1234, manifests={'sha256':'abcd', 'sha1new':'deff'})
			m.with_children(extract = k.get('extract', None))
			m.with_children(type = k.get('type', None))
			return m

		modify(feed_module).Archive = mkarchive
		self.proj = mock('project', create_children = False).with_children(
			homepage='http://example.com/project',
			id='upstream_id',
			upstream_type='upstream_mock',
			latest_version=CompositeVersion('2.5.1'),
			versions=[CompositeVersion('0.1'), CompositeVersion('2.5.1')],
			summary='the BEST project',
			description='use it for all your projecty needs!',
			implementation_for = lambda v: mock('release ' + v.upstream).with_children(
				version=v,
				url='http://example.com/download-' + v.upstream,
				released='2012-01-01',
				extract = None,
				archive_type='text/awesome')
		)

		self.proj2 = mock('project2', create_children = False).with_children(
			homepage='http://example.com/project2',
			id='upstream_id2',
			upstream_type='upstream_mock2',
			latest_version='2.5.12',
			versions=['0.1', '2.5.12'],
			summary='the BEST project2',
			description='use it for all your projecty needs!2',
			implementation_for = lambda v: mock('release ' + v.upstream).with_children(
				version=v,
				url='http://example.com/download-' + v.upstream,
				archive_type=None,
				extract = None,
				released='2012-01-012'),
		)
		self.clear_buffer()
	
	def clear_buffer(self):
		self.buffer = StringIO()
	
	def saved_dom(self):
		xml = self.buffer.getvalue()
		return ParseXML(xml, selfClosingTags='archive manifest-digest gfxmonk:publish gfxmonk:upstream'.split()).interface

	def write_initial_feed(self, proj, add_impl = False):
		feed = Feed.from_project(proj, 'http://example.com/')
		if add_impl:
			feed.add_implementation()
		feed.save(self.buffer)
		self.buffer.seek(0)
	
	def assert_details_match(self, project):
		saved_dom = self.saved_dom()
		self.assertEqual(saved_dom.find('homepage').text, project.homepage)
		self.assertEqual(saved_dom.find('summary').text, project.summary)
		self.assertEqual(saved_dom.find('description').text, project.description)
		upstream_attrs = dict(saved_dom.find('gfxmonk:upstream').attrs)
		self.assertEqual(upstream_attrs, {'type': project.upstream_type, 'id': project.id})
		self.assertNotEqual(saved_dom.find('group'), None)

	def assert_impl_matches(self, impl, project, size, manifests, type=None):
		expected_impl = project.implementation_for(project.latest_version)
		self.assertEqual(impl['version'], str(expected_impl.version.derived))
		self.assertEqual(impl['released'], expected_impl.released)
		self.assertEqual(impl['id'], "sha1new=%s" % manifests['sha1new'])
		manifest = impl.find('manifest-digest')
		archive = impl.find('archive')
		self.assertEqual(archive['href'], expected_impl.url)
		self.assertEqual(archive['size'], str(size))
		if type is not None:
			self.assertEqual(archive['type'], type)
		manifest_attrs = manifest.attrs
		assert len(manifest_attrs) == 1
		manifest_found = manifest_attrs[0]
		self.assertEqual(manifest_found, ('sha256', manifests['sha256']))

	def test_feed_creation(self):
		feed = Feed.from_project(self.proj, "http://example.com/dist/0install/my-project.xml")
		feed.save(self.buffer)
		output = self.saved_dom()
		self.assertEqual(output['uri'], 'http://example.com/dist/0install/my-project.xml')
		self.assert_details_match(self.proj)
		self.assertEqual(output.find('name').text, 'my-project')
	
	def test_update_details(self):
		self.write_initial_feed(self.proj)
		modify(SOURCES)['upstream_mock'] = lambda **kw: self.proj2
		feed = Feed.from_file(self.buffer)
		self.assertEqual(feed.project, self.proj2)

		feed.update_metadata()
		self.clear_buffer()
		feed.save(self.buffer)
		self.assert_details_match(self.proj2)
	
	def test_add_implementation_without_modifying_details(self):
		self.write_initial_feed(self.proj)
		modify(SOURCES)['upstream_mock'] = lambda **kw: self.proj

		feed = Feed.from_file(self.buffer)
		self.assertEqual(feed.project, self.proj)

		feed.add_implementation()
		self.clear_buffer()
		feed.save(self.buffer)

		output = self.saved_dom()
		implementations = output.findAll('implementation')
		self.assertEqual(len(implementations), 1, repr(implementations))
		impl = implementations[0]
		self.assertEqual(impl["version"], str(self.proj.latest_version.derived))
		self.assert_impl_matches(impl, self.proj, size=1234, manifests={'sha256':'abcd', 'sha1new':'deff'}, type='text/awesome')

	@ignore
	def test_add_initial_implementation_to_source_group(self):
		pass
	@ignore
	def test_add_another_implementation_to_source_group(self):
		pass

	def test_detects_new_release(self):
		self.write_initial_feed(self.proj, add_impl = True)
		modify(SOURCES)['upstream_mock'] = lambda **kw: self.proj2

		feed = Feed.from_file(self.buffer)
		self.assertEquals(feed.unpublished_versions(newest_only=True), set(['2.5.12']))

	def test_detects_all_unpublished_versions(self):
		self.write_initial_feed(self.proj, add_impl = True)
		modify(SOURCES)['upstream_mock'] = lambda **kw: self.proj2
		feed = Feed.from_file(self.buffer)
		self.assertEquals(feed.unpublished_versions(newest_only=False), set(['0.1', '2.5.12']))

	def test_detects_up_to_date_feed(self):
		self.write_initial_feed(self.proj, add_impl = True)
		modify(SOURCES)['upstream_mock'] = lambda **kw: self.proj

		feed = Feed.from_file(self.buffer)
		self.assertEquals(feed.unpublished_versions(newest_only=True), set([]))

	def test_detects_feed_with_all_implementations_added(self):
		self.write_initial_feed(self.proj, add_impl = True)
		modify(SOURCES)['upstream_mock'] = lambda **kw: self.proj

		feed = Feed.from_file(self.buffer)
		feed.add_implementation('0.1')
		self.assertEquals(feed.unpublished_versions(), set([]))

class TestFeedProcessing(TestCase):
	@ignore
	def test_constructing_pypi_project_from_feed(self):
		pass
	@ignore
	def test_constructing_github_project_from_feed(self):
		pass
	@ignore
	def test_constructing_with_arbitrary_attributes(self):
		pass
