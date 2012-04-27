from .pypi import Pypi
from .github import Github

SOURCES = {
	'pypi': Pypi,
	'github': Github
}

def make(**k):
	"""Given a dict of attributes, grabs the class from the
	`type` key and passes all remaining attributes onto the
	project class constructor, returning the instance"""
	k = k.copy()
	project_type = k.pop('type')
	try:
		return SOURCES[project_type](**k)
	except KeyError:
		raise ValueError("no such project type: %s" % (project_type,))

def guess_project(url, **kw):
	'''return a project from a URL (and optional additional attributes)'''
	kw = kw.copy()
	kw.update(guess_project_info(url))
	return make(**kw)

def guess_project_info(url):
	'''Return a dict of project attrs from a URL,
	suitable for passing into `make`
	(most users will want `guess_project` instead
	of this method, as it calls `make` for you.'''
	for cls in SOURCES.values():
		try:
			return cls.parse_uri(url)
		except ValueError:
			continue
	else:
		raise ValueError("unknown project type with URL: %s" % (url,))
