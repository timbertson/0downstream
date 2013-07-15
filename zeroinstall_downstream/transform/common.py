class DefaultTransform():

	def process_implementation(data):
		implementation = data.implementation
		archive = data.archive
		config = data.config
		feed = data.feed
		package_id = data.package_id

		# emulate the default extract behaviour of 0publish:
		if archive.extract is None:
			contents = os.listdir(archive.local)
			if len(contents) == 1:
				archive.extract = contents[0]

