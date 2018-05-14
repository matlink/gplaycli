import os
import sys
import math
import time


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

### progress bar ###
""" copyright https://github.com/kennethreitz/clint """
STREAM = sys.stderr

BAR_TEMPLATE = '%s[%s%s] %i/%i - %s\r'

BAR_FILLED_CHAR = '#'
BAR_EMPTY_CHAR = ' '

# How long to wait before recalculating the ETA
ETA_INTERVAL = 1
# How many intervals (excluding the current one) to calculate the simple moving
# average
ETA_SMA_WINDOW = 9

class progressbar(object):
	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.done()
		return False  # we're not suppressing exceptions

	def __init__(self, label='', width=32, hide=None, empty_char=BAR_EMPTY_CHAR,
				 filled_char=BAR_FILLED_CHAR, expected_size=None, every=1):
		self.label = label
		self.width = width
		self.hide = hide
		# Only show bar in terminals by default (better for piping, logging etc.)
		if hide is None:
			try:
				self.hide = not STREAM.isatty()
			except AttributeError:  # output does not support isatty()
				self.hide = True
		self.empty_char = empty_char
		self.filled_char = filled_char
		self.expected_size = expected_size
		self.every = every
		self.start = time.time()
		self.ittimes = []
		self.eta = 0
		self.etadelta = time.time()
		self.etadisp = self.format_time(self.eta)
		self.last_progress = 0
		if (self.expected_size):
			self.show(0)

	def show(self, progress, count=None):
		if count is not None:
			self.expected_size = count
		if self.expected_size is None:
			raise Exception("expected_size not initialized")
		self.last_progress = progress
		if (time.time() - self.etadelta) > ETA_INTERVAL:
			self.etadelta = time.time()
			self.ittimes = \
				self.ittimes[-ETA_SMA_WINDOW:] + \
					[-(self.start - time.time()) / (progress+1)]
			self.eta = \
				sum(self.ittimes) / float(len(self.ittimes)) * \
				(self.expected_size - progress)
			self.etadisp = self.format_time(self.eta)
		x = int(self.width * progress / self.expected_size)
		if not self.hide:
			if ((progress % self.every) == 0 or	  # True every "every" updates
				(progress == self.expected_size)):   # And when we're done
				STREAM.write(BAR_TEMPLATE % (
					self.label, self.filled_char * x,
					self.empty_char * (self.width - x), progress,
					self.expected_size, self.etadisp))
				STREAM.flush()

	def done(self):
		self.elapsed = time.time() - self.start
		elapsed_disp = self.format_time(self.elapsed)
		if not self.hide:
			# Print completed bar with elapsed time
			STREAM.write(BAR_TEMPLATE % (
				self.label, self.filled_char * self.width,
				self.empty_char * 0, self.last_progress,
				self.expected_size, elapsed_disp))
			STREAM.write('\n')
			STREAM.flush()

	def format_time(self, seconds):
		return time.strftime('%H:%M:%S', time.gmtime(seconds))
