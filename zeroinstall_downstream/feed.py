TEMPLATE="""<?xml version="1.0" ?>
<?xml-stylesheet type='text/xsl' href='interface.xsl'?>
<interface xmlns="http://zero-install.sourceforge.net/2004/injector/interface" xmlns:gfxmonk="http://gfxmonk.net/dist/0install" xmlns:compile="http://zero-install.sourceforge.net/2006/namespaces/0compile">
	<name></name>
	<summary></summary>
	<gfxmonk:publish mode="third-party"/>
	<description>
	</description>
	<homepage></homepage>

	<group>
	</group>
</interface>
"""

from xml.dom import minidom

ZI = "http://zero-install.sourceforge.net/2004/injector/interface"
GFXMONK = "http://gfxmonk.net/dist/0install"
ZEROCOMPILE = "http://zero-install.sourceforge.net/2006/namespaces/0compile"

class Feed(object):
	def __init__(self, doc, uri, project=None):
		self.doc = doc
		self.uri = uri
		self.project = project
		self.interface = doc.documentElement
		self.interface.setAttribute("xmlns:gfxmonk", GFXMONK)
		self.interface.setAttribute("xmlns:0compile", ZEROCOMPILE)

	@classmethod
	def from_project(cls, project, dest_uri):
		dom = minidom.getDOMImplementation()
		doc = dom.createDocument(ZI, "interface", None)
		feed = cls(doc, project=project, uri = dest_uri)
		feed.update_metadata()
		group = feed._mknode("group")
		feed.interface.appendChild(group)
		return feed

	def update_metadata(self):
		self.interface.setAttribute('uri', self.uri)
		name = self._create_or_update_child_node(self.interface, "name", self.name)
		summary = self._create_or_update_child_node(self.interface, "summary", self.project.summary)
		project_info = self._create_or_update_child_node(self.interface, "gfxmonk:upstream", ns=GFXMONK)
		project_info.setAttribute('type', self.project.upstream_type)
		project_info.setAttribute('id', self.project.upstream_id)
		publish = self._create_or_update_child_node(self.interface, "gfxmonk:publish", "third-party", ns=GFXMONK)
		homepage = self._create_or_update_child_node(self.interface, "homepage", self.project.homepage)
		description = self._create_or_update_child_node(self.interface, "description", self.project.description)

	def _create_or_update_child_node(self, elem, node_name, content=None, ns=None):
		children = elem.childNodes
		for child in children:
			if child.tagName == node_name:
				new_node = child
				while new_node.hasChildNodes():
					_del = new_node.removeChild(new_node.childNodes[0])
				break
		else:
			new_node = self._mknode(node_name)
			if elem.hasChildNodes() and elem.getElementsByTagName('group'):
				first_group = elem.getElementsByTagName('group')[0]
				elem.insertBefore(new_node, first_group)
			else:
				elem.appendChild(new_node)
		if content is not None:
			content = self.doc.createTextNode(content)
			new_node.appendChild(content)
		return new_node

	def _mknode(self, node_name, content=None, ns=None):
		if ns is None:
			node = self.doc.createElement(node_name)
		else:
			node = self.doc.createElementNS(ns, node_name)
		if content is not None:
			content = self.doc.createTextNode(content)
			node.appendChild(content)
		return node

	@classmethod
	def from_feed(cls, infile):
		pass

	@property
	def has_new_implementations(self):
		pass

	@property
	def name(self):
		assert '/' in self.uri, "Bad URI: %s" % (self.uri,)
		return self.uri.rstrip('/').rsplit('/', 1)[1].rsplit('.', 1)[0]

	def add_impl(self, impl):
		pass

	@property
	def xml(self):
		return self.doc.toprettyxml(indent='')

	def save(self, outfile):
		self.doc.writexml(outfile)

