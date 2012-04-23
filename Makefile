
0downstream-local.xml: 0downstream.xml
	0launch http://gfxmonk.net/dist/0install/0local.xml 0downstream.xml

test: phony 0downstream-local.xml
	0launch --command=test 0downstream-local.xml

test-local: phony 0downstream-local.xml
	0launch --command=test 0downstream-local.xml --exclude='remote'

notebook: phony 0downstream-local.xml
	(sleep 2; chromium-browser http://127.0.0.1:8888)&
	0launch --command=notebook 0downstream-local.xml

.PHONY: phony


