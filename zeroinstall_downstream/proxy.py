from __future__ import print_function

import os
import traceback
import shutil
import collections
import contextlib
import threading
import hashlib
import re
import logging
import time

from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urllib2
from SocketServer import ThreadingMixIn

root = os.path.realpath('.')
cache_root = os.path.join(root, 'http.cache')
logger = logging.getLogger(__name__)

try:
	from urlparse import urlparse #py2
except ImportError:
	from urllib.parse import urlparse #py3

def safe_name(url):
	parsed = urlparse(url)
	domain = parsed.netloc
	digest = hashlib.md5(url).hexdigest()[:12]
	filename = parsed.path.rstrip('/').split('/')[-1]
	filename = re.sub('[^-._a-zA-Z0-9]+', '-', filename)
	# print(repr((domain, filename, digest)))
	return domain + "-" + filename + "-" + digest + ".cache"

def run(opts):
	try:
		del os.environ['http_proxy']
	except KeyError: pass
	config = opts.config

	cache_lock = collections.defaultdict(lambda: threading.Lock())

	if not os.path.exists(cache_root):
		os.path.mkdir(cache_root)
	
	@contextlib.contextmanager
	def cached(url):
		cache_lock[url].acquire()
		path = config.local_path_for(url)
		try:
			if path is None:
				# cache from real location
				path = os.path.join(cache_root, safe_name(url))
				cached = False
				try:
					st = os.stat(path)
				except OSError:
					pass
				else:
					# delete old resources
					max_age = opts.max_age
					evict = False
					if max_age >= 0:
						now = time.time()
						mtime = st.st_mtime
						expiry_date = st.st_mtime + (max_age * 60 * 60)
						logger.warn("expiry date = %s (now=%s)" % (expiry_date, now))
						if mtime > now or expiry_date < now:
							evict = True
					if evict:
						logger.debug("evicting cached %s" % url)
					else:
						logger.debug("serving cached %s" % url)
						cached = True

				if not cached:
					logger.debug("caching to %s" % path)
					with open(path, 'w+b') as output:
						with contextlib.closing(urllib2.urlopen(url)) as stream:
							shutil.copyfileobj(stream, output)

				yield path

			else:
				# serve directly from local feeds
				path = os.path.abspath(path)
				if not path.startswith(root):
					raise Exception("Attempt to fetch file outside of '%s': %s'" % (root, path))
				yield path
		finally:
			cache_lock[url].release()


	class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
		pass

	class Proxy(SimpleHTTPRequestHandler):
		def do_GET(self):
			try:
				url = self.path
				with cached(url) as path:
					st = os.stat(path)
					headers = [('Content-Length', os.stat(path).st_size)]
					with open(path) as stream:
						self.send_response(200)
						for name, val in headers:
							self.send_header(name, val)
						self.end_headers()
						self.copyfile(stream, self.wfile)

			except Exception as e:
				traceback.print_exc()
				self.send_error(500, "Error: %s" % e)

	httpd = ThreadedHTTPServer(('127.0.0.1', opts.port), Proxy)
	print("To use:\nenv http_proxy='http://localhost:%s/'" % (opts.port,))
	try:
		httpd.serve_forever()
	except:
		httpd.socket.close()
		raise
