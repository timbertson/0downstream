import functools
from version import Version
import logging
LOGGER = logging.getLogger(__name__)

def try_parse(version_string):
	try:
		LOGGER.debug("trying to parse: %s", version_string)
		return CompositeVersion(version_string)
	except ValueError:
		LOGGER.debug("ignoring unparseable version: %s", version_string)
		return None

@functools.total_ordering
class CompositeVersion(object):
	def __init__(self, version_string, derived=None):
		assert isinstance(version_string, basestring), "Expected string, got %s" % (type(version_string))
		self.upstream = version_string
		if derived is None:
			derived = Version.parse(version_string, coerce=True)
		assert isinstance(derived, Version)
		self.derived = derived
	
	# note that two versions are equal if their derived version is equal, regardless
	# of the upstream text.
	def __eq__(self, other):
		assert isinstance(other, type(self)), "Comparing %s to %s" % (type(self), type(other))
		return self.derived == other.derived and self.upstream == other.upstream

	def __hash__(self):
		return hash(self.derived)

	def __ne__(self, other): return not self.__eq__(other)
	def __lt__(self, other):
		assert isinstance(other, type(self)), "Comparing %s to %s" % (type(self), type(other))
		if self.derived == other.derived:
			return self.upstream < other.upstream
		return self.derived < other.derived

	def __repr__(self):
		return "<#CompositeVersion: %s | %s>" % (self.upstream, self.derived)

	@property
	def exact(self):
		return str(self.derived) == self.upstream

	def pretty(self):
		if self.exact: return self.upstream
		return "%s (%s)" % (self.derived, self.upstream)

	def fuzzy_match(self, version_str):
		return version_str in (str(self.derived), self.upstream)
