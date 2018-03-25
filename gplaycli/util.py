import os
import math
from etaprogress.progress import ProgressBar

def sizeof_fmt(num):
	log = int(math.log(num, 1024))
	return "%.2f%s" % (num/(1024**log), ['bytes','KB','MB','GB','TB'][log])

def load_from_file(filename):
	return [package.strip('\r\n') for package in open(filename).readlines()]

def list_folder_apks(folder):
	"""
	List apks in the given folder
	"""
	list_of_apks = [filename for filename in os.listdir(folder) if filename.endswith(".apk")]
	return list_of_apks

def vcode(string_vcode):
	"""
	return integer of version
	base can be 10 or 16
	"""
	base = 10
	if string_vcode.startswith('0x'):
		base = 16
	return int(string_vcode, base)

class bar(ProgressBar):
	def __init__(self, expected_size, hide=False, *args, **kwargs):
		ProgressBar.__init__(self, expected_size, *args, **kwargs)
		self.hide = hide

	def show(self, numerator):
		if self.hide:
			return
		self.numerator = numerator
		print(self, end='\r')

	def done(self):
		if self.hide:
			return
		print()
