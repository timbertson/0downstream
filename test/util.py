from __future__ import print_function
import sys
import os
import time
import socket
import threading
from mocktest import *
from zeroinstall_downstream import proxy
import downstream_config

def init_tests():
	class Object(object): pass

	opts = Object()
	opts.port = 8084
	opts.max_age = -1
	opts.config = downstream_config

	proxy_thread = threading.Thread(target=lambda: proxy.run(opts))
	proxy_thread.daemon=True
	proxy_thread.start()

	# wait until the proxy's ready
	os.environ['http_proxy'] = 'http://localhost:%d/' % opts.port
	s = socket.socket()
	try:
		while s.connect_ex(('localhost', opts.port)) != 0:
			# print("waiting for proxy...", file=sys.stderr)
			time.sleep(0.1)
	finally:
		s.close()

init_tests()
