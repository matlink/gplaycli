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
	rm -f ~/.cache/gplaycli/token
	$(PROJECT) -vd $(TESTAPK)
	[ -f $(TESTAPK).apk ]
	$(PROJECT) -vd $(TESTAPK) -f download
	[ -f download/$(TESTAPK).apk ]
	$(PROJECT) -vyu tests
	$(PROJECT) -s fire -n 30 | wc -l
	$(PROJECT) -s com.yogavpn
	$(PROJECT) -s com.yogavpn -n 15
	$(PROJECT) -vd $(TESTAPK) -dc hammerhead
	$(PROJECT) -d com.mapswithme.maps.pro -a
	[ -f com.mapswithme.maps.pro.apk ]
	[ -f main.*.com.mapswithme.maps.pro.obb ]
	[ -f patch.*.com.mapswithme.maps.pro.obb ]
