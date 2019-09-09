SHELL := /bin/bash
PYTHON=$(shell which python3)
GPG=$(shell which gpg2)
TWINE=$(shell which twine)
VERSION=$(shell $(PYTHON) setup.py --version)
GPGID=186BB3CA

source:
	$(PYTHON) setup.py sdist

sign:
	$(GPG) --detach-sign --default-key $(GPGID) -a dist/GPlayCli-$(VERSION).tar.gz

publish: clean source sign
	$(TWINE) upload dist/GPlayCli-$(VERSION).tar.gz dist/GPlayCli-$(VERSION).tar.gz.asc

clean:
	$(PYTHON) setup.py clean
	rm -rf build/ MANIFEST dist GPlayCli.egg-info debian/{gplaycli,python-module-stampdir} debian/gplaycli.{debhelper.log,postinst.debhelper,prerm.debhelper,substvars} *.tar.gz* deb_dist
	find . -name '*.pyc' -delete

patch:
	patch setup.py debian/0001-conf-install-path.patch

deb: patch
	mkdir -p packages
	bash debian/build.sh