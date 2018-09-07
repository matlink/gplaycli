import os
import sys
import math
import time

def sizeof_fmt(num):
	if not num:
		return "00.00KB"
	log = int(math.log(num, 1024))
	return "%.2f%s" % (num/(1024**log), ['B ','KB','MB','GB','TB'][log])

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
class progressbar(object):
	def __init__(self, label='', width=32, hide=None, empty_char=' ',
				 filled_char='#', expected_size=None, every=1, eta_interval=1,
				 eta_sma_window=9, stream=sys.stderr, bar_template='%s[%s%s] %s/%s - %s %s/s\r'):
		self.label = label
		self.width = width
		self.hide = hide
		# Only show bar in terminals by default (better for piping, logging etc.)
		if hide is None:
			try:
				self.hide = not stream.isatty()
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
		self.eta_interval = eta_interval
		self.eta_sma_window = eta_sma_window
		self.stream = stream
		self.bar_template = bar_template
		self.speed = 0
		if (self.expected_size):
			self.show(0)

	def show(self, progress, count=None):
		if count is not None:
			self.expected_size = count
		if self.expected_size is None:
			raise Exception("expected_size not initialized")
		self.last_progress = progress
		if (time.time() - self.etadelta) > self.eta_interval:
			self.etadelta = time.time()
			self.ittimes = (self.ittimes[-self.eta_sma_window:]
							+ [-(self.start - time.time()) / (progress+1)])
			self.eta = (sum(self.ittimes) / float(len(self.ittimes))
						* (self.expected_size - progress))
			self.etadisp = self.format_time(self.eta)
			self.speed = 1 / (sum(self.ittimes) / float(len(self.ittimes)))
		x = int(self.width * progress / self.expected_size)
		if not self.hide:
			if ((progress % self.every) == 0 or	  # True every "every" updates
				(progress == self.expected_size)):   # And when we're done
				self.stream.write(self.bar_template % (
					self.label, self.filled_char * x,
					self.empty_char * (self.width - x), sizeof_fmt(progress),
					sizeof_fmt(self.expected_size), self.etadisp, sizeof_fmt(self.speed)))
				self.stream.flush()

	def done(self):
		self.elapsed = time.time() - self.start
		elapsed_disp = self.format_time(self.elapsed)
		if not self.hide:
			# Print completed bar with elapsed time
			self.stream.write(self.bar_template % (
				self.label, self.filled_char * self.width,
				self.empty_char * 0, sizeof_fmt(self.last_progress),
				sizeof_fmt(self.expected_size), elapsed_disp, sizeof_fmt(self.speed)))
			self.stream.write('\n')
			self.stream.flush()

	@staticmethod
	def format_time(seconds):
		return time.strftime('%H:%M:%S', time.gmtime(seconds))
