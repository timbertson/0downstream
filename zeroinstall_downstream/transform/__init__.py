import os
import logging
logger = logging.getLogger(__name__)
from . import npm, common

def default_for(project, archive):
	type = project.upstream_type
	# if type == 'github':
	# 	type = guess_type(archive)
	# 	logging.debnug("Guessed type %s" % (type,))
	return globals().get(type, 'common')

# def guess_type(archive):
# 	# look two directories deep, to work around any
# 	# leading "extract" directories
# 	files = list(os.listdir(archive.local))
# 	for file in files:
# 		path = os.path.join(archive,local, file)
# 		if os.path.isdir(path):
# 			files.extend(os.listdir(path))
#
# 	logging.debug("Guessing language type from filenames: %r" % (files,))
# 	if 'Gemfile' in root_files: return 'rubygems'
# 	if 'package.json' in root_files: return 'npm'
# 	if 'setup.py' in root_files: return 'pypi'
# 	return None
