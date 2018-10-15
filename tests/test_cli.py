import os
import sys
import hashlib
import pytest
import subprocess as sp
import re
import json

ENC = sys.getdefaultencoding()
ERR = 'replace'

TESTAPK='org.mozilla.focus'
UPDATEAPK=os.path.join("tests", "org.mozilla.focus.20112247.apk")
TOKENFILE=os.path.expanduser('~/.cache/gplaycli/token')

RE_APPEND_VERSION=re.compile("^"+TESTAPK.replace('.', r'\.')+r"-v.[A-z0-9.-]+\.apk$")

def call(args):
	proc = sp.run(args.split(), stdout=sp.PIPE, stderr=sp.PIPE)
	print(proc.stdout.decode(ENC, ERR), file=sys.stdout)
	print(proc.stderr.decode(ENC, ERR), file=sys.stderr)
	return proc

def nblines(comp_proc):
	return len(comp_proc.stdout.decode(ENC, ERR).splitlines(True))

def download_apk(append_version = False):
	if append_version:
		call("gplaycli -av -vd %s" % TESTAPK)
	else:
		call("gplaycli -vd %s" % TESTAPK)

def checksum(apk):
	return hashlib.sha256(open(apk, 'rb').read()).hexdigest()

def test_download():
	if os.path.isfile(TOKENFILE):
		os.remove(TOKENFILE)
	download_apk()
	assert os.path.isfile("%s.apk" % TESTAPK)

def test_download_version():
	if os.path.isfile(TOKENFILE):
		os.remove(TOKENFILE)
	download_apk(append_version = True)

	found = False
	for f in os.listdir():
		if RE_APPEND_VERSION.match(f):
			found = True
	if not found:
		pytest.fail("Could not find package with version appended")

def test_alter_token():
	cache_dict = json.loads(open(TOKENFILE).read())
	cache_dict['token'] = ' ' + cache_dict['token'][1:]
	with open(TOKENFILE, 'w') as outfile:
		print(json.dumps(cache_dict), file=outfile)
	download_apk()
	assert os.path.isfile("%s.apk" % TESTAPK)

def test_update(apk=UPDATEAPK):
	before = checksum(apk)
	call("gplaycli -vyu tests")
	after = checksum(apk)
	assert after != before

def test_search(string='fire', number=30):
	c = call("gplaycli -s %s -n %d" % (string, number))
	assert c.returncode == 0
	assert nblines(c) <= number + 1

def test_search2(string='com.yogavpn'):
	c = call("gplaycli -s %s" % string)
	assert c.returncode == 0
	assert nblines(c) >= 0

def test_search3(string='com.yogavpn', number=15):
	c = call("gplaycli -s %s -n %d" % (string, number))
	assert c.returncode == 0
	assert nblines(c) <= number + 1

def test_another_device(device='hammerhead'):
	call("gplaycli -vd %s -dc %s" % (TESTAPK, device))
	assert os.path.isfile("%s.apk" % TESTAPK)

def test_download_additional_files(apk='com.mapswithme.maps.pro', device='angler'):
	call("gplaycli -d %s -a -dc %s" % (apk, device))
	assert os.path.isfile("%s.apk" % apk)
	files = [f for f in os.listdir() if os.path.isfile(f)]
	assert any([f.endswith('%s.obb' % apk) and f.startswith('main') for f in files])
	assert any([f.endswith('%s.obb' % apk) and f.startswith('patch') for f in files])
