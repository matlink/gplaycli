# $Id: Makefile,v 1.6 2015/08/24 22:00:00 Matlink Exp $
#
SHELL := /bin/bash
PYTHON=`which python`
DESTDIR=/
BUILDIR=$(CURDIR)/debian/gplaycli
PROJECT=gplaycli
VERSION=0.1

all:
	@echo "make source - Create source package"
	@echo "make install - Install on local system"
	@echo "make builddeb - Generate a deb package"
	@echo "make clean - Get rid of scratch and byte files"

source:
	$(PYTHON) setup.py sdist $(COMPILE)

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

deb:
#	python setup.py --command-packages=stdeb.command bdist_deb
	python setup.py --command-packages=stdeb.command sdist_dsc --sign-results bdist_deb
#	python setup.py sdist_dsc --sign-results bdist_deb

clean:
	$(PYTHON) setup.py clean
	rm -rf build/ MANIFEST dist GPlayCli.egg-info debian/{gplaycli,python-module-stampdir} debian/gplaycli.{debhelper.log,postinst.debhelper,prerm.debhelper,substvars} *.tar.gz* deb_dist
	find . -name '*.pyc' -delete
