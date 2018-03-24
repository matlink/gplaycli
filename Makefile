SHELL := /bin/bash
PYTHON=$(shell which python3)
GIT=$(shell which git)
GPG=$(shell which gpg2)
TWINE=$(shell which twine)
BUILDIR=$(CURDIR)/debian/gplaycli
PROJECT=gplaycli
VERSION=$(shell $(PYTHON) setup.py --version)
GPGID=186BB3CA
PYTEST=$(shell which py.test)
TESTAPK=org.mozilla.focus

all: test

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

test:
	$(PYTEST) tests/
