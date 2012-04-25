from .pypi import Pypi
from .github import Github

SOURCES = {
	'pypi': Pypi,
	'github': Github
}

def make(**k):
	k = k.copy()
	project_type = k.pop('type')
	try:
		return SOURCES[project_type](**k)
	except KeyError:
		raise ValueError("no such project type: %s" % (project_type,))



