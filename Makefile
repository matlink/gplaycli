# $Id: Makefile,v 1.6 2015/08/24 22:00:00 Matlink Exp $
#
SHELL := /bin/bash
PYTHON=$(shell which python3)
GIT=$(shell which git)
GPG=$(shell which gpg2)
TWINE=$(shell which twine)
DESTDIR=/
BUILDIR=$(CURDIR)/debian/gplaycli
PROJECT=gplaycli
VERSION=$(shell $(PYTHON) setup.py --version)
GPGID=186BB3CA
PYTEST=$(shell which py.test)
TESTAPK=org.mozilla.focus

all:
	@echo "make source - Create source package"
	@echo "make install - Install on local system"
	@echo "make builddeb - Generate a deb package"
	@echo "make clean - Get rid of scratch and byte files"

source:
	$(PYTHON) setup.py sdist $(COMPILE)

sign:
	$(GPG) --detach-sign --default-key $(GPGID) -a dist/GPlayCli-$(VERSION).tar.gz

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

deb:
	$(PYTHON) setup.py --command-packages=stdeb.command sdist_dsc --sign-results bdist_deb

publish: clean source sign
	$(TWINE) upload dist/GPlayCli-$(VERSION).tar.gz dist/GPlayCli-$(VERSION).tar.gz.asc

gitpush:
	$(GIT) push origin master
	$(GIT) push github master
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
	[[ `$(PROJECT) -s fire -n 30 | wc -l` -eq 31 ]]
	$(PROJECT) -s com.yogavpn
	$(PROJECT) -s com.yogavpn -n 15
	$(PROJECT) -vd $(TESTAPK) -dc hammerhead
	$(PROJECT) -d com.mapswithme.maps.pro -a
	[ -f com.mapswithme.maps.pro.apk ]
	[ -f main.*.com.mapswithme.maps.pro.obb ]
	[ -f patch.*.com.mapswithme.maps.pro.obb ]
