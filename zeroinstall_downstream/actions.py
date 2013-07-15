import os
import shutil
import logging
import tempfile
import subprocess

from . import api
from .feed import Feed

logger = logging.getLogger(__name__)

_seen = set()
indent = 0
INDENT = ""

def _visit(location):
	if location in _seen: return False
	_seen.add(location)
	return True

import contextlib
@contextlib.contextmanager
def _indented():
	global INDENT,indent
	try:
		indent += 1
		INDENT = "  " * indent
		yield
	finally:
		indent -= 1
		INDENT = "  " * indent

class AlreadyPublished(RuntimeError):
	def __init__(self, version):
		self.version = version
		super(AlreadyPublished, self).__init__("already published: %s" % (version,))

def _save_feed(feed, location, opts):
	feed.make_canonical()
	feed.save_to_path(location.path)
	_feed_modified(location, opts)

def _feed_modified(location, opts):
	opts.config.feed_modified(location.path)

@contextlib.contextmanager
def _release_feed(project, location, version, opts):
	if version is None:
		version = project.latest_version
	else:
		version = project.find_version(version)

	if not opts.recreate and os.path.exists(location.path):
		published = Feed.from_path(location.path).published_versions
		if version.derived in published:
			raise AlreadyPublished(version.derived)

	release = project.get_release(version)
	project_api = api.Release(project, release, location, opts)
	with project_api:
		logger.info("%sprocessing %s:%s v%s" % (INDENT, project.upstream_type, project.id, version.derived))
		opts.config.process(project_api)
		# if that all worked, generate the _real_ feed
		local = project_api.generate_feed()
		yield local

def update(project, location, version, opts):
	if not _visit(location):
		logger.info("%sskipping already-updated %s" % location)
		return

	logger.info("%sUpdating %s" % (INDENT, location.path))

	with _indented():
		if opts.recreate:
			# create a new master feed that we'll add each previously-published version to:
			feed = Feed.from_path(location.path)

			with tempfile.NamedTemporaryFile() as master:
				for i, version in enumerate(feed.published_versions):
					logger.info("adding version %s" % version)
					version = project.find_version(version)
					with _release_feed(project, location, version, opts) as local:
						if i == 0:
							shutil.copyfile(local, master.name)
						else:
							subprocess.check_call(['0publish', '--add-from', local, master.name])
				# once we've successfully added every version, save the results
				_save_feed(Feed(master), location, opts)
		else:
			try:
				with _release_feed(project, location, version, opts) as local:
					subprocess.check_call(['0publish', '--add-from', local, location.path])
					_feed_modified(location, opts)
			except AlreadyPublished as e:
				logger.info("feed %s already contains version %s" % (location.path, e.version))
				_feed_modified(location, opts)

def create(project, location, version, opts):
	if not _visit(location):
		logger.info("%sskipping already-updated %s" % (INDENT, location))
		return
	logger.info("%sCreating %s" % (INDENT, location.path))
	assert not os.path.exists(location.path)

	with _indented():
		with _release_feed(project, location, version, opts) as local:
			assert not os.path.exists(location.path)
			feed = Feed.from_path(local)
			feed.make_canonical()
			feed.save_to_path(location.path)

def update_info(project, location, opts):
	feed = Feed.from_path(location.path)
	feed.update_metadata(project, location)
	_save_feed(feed, location, opts)
