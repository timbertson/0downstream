class Tag(object):
	def __init__(self, tag, attrs=None, children=None, text=None, namespace=None):
		self.tag      = tag
		self.attrs    = {} if attrs    is None else attrs
		if text is not None:
			assert children is None
			self.children = [text]
		else:
			self.children = [] if children is None else children

		self.namespace = namespace
	
	def attr(self, name, val):
		assert name not in self.attrs, "%s already set for %r" % (name, self)
		self.attrs[name] = val
	
	def __repr__(self):
		return '#<%s %r, children=%r>' % (self.tag, self.attrs, self.children)

	def __getitem__(self, key):
		return self.attrs[key]

	def __setitem__(self, key, val):
		self.attrs[key] = val

	def __contains__(self, key):
		return key in self.attrs
	
	def __hash__(self):
		return hash(self.tag, self.attrs)

	def __eq__(self, other):
		return (
			type(self) == type(other)
			and self.tag == other.tag
			and self.namespace == other.namespace
			and self.attrs == other.attrs
			and self.children == other.children
		)

	def __ne__(self, other): return not self.__eq__(other)

	def append(self, child):
		self.children.append(child)
	
	def get(self, key, default=None):
		return self.attrs.get(key, default)
	
	def copy(self):
		return Tag(self.tag, self.attrs.copy(), self.children[:])
	
	def addTo(self, parent, doc):
		if self.namespace is None:
			elem = doc.createElement(self.tag)
		else:
			elem = doc.createElementNS(self.namespace, self.tag)
		for name, val in self.attrs.items():
			elem.setAttribute(name, str(val))
		for child in self.children:
			if isinstance(child, str) or isinstance(child, unicode):
				elem.appendChild(doc.createTextNode(child))
			else:
				child.addTo(elem, doc)
		parent.appendChild(elem)
		return elem

class Attribute(object):
	def __init__(self, name, val, namespace=None):
		self.name = name
		self.val = val
		self.namespace = namespace
	
	def addTo(self, elem, doc):
		if self.namespace:
			elem.setAttributeNS(self.namespace, self.name, self.val)
		else:
			elem.setAttribute(self.name, self.val)
		return elem
