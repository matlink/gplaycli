#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPlay-Cli
Copyleft (C) 2015 Matlink
Hardly based on GooglePlayDownloader https://framagit.org/tuxicoman/googleplaydownloader
Copyright (C) 2013 Tuxicoman

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any
later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.
You should have received a copy of the GNU Affero General Public License along with this program.  If not,
see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import json
import enum
import logging
import argparse
import requests
import configparser

from gpapi.googleplay import GooglePlayAPI, LoginError, RequestError
from google.protobuf.message import DecodeError
from pkg_resources import get_distribution, DistributionNotFound
from pyaxmlparser import APK

from . import util
from . import hooks

try:
	import keyring
	HAVE_KEYRING = True
except ImportError:
	HAVE_KEYRING = False


try:
	__version__ = '%s [Python%s] ' % (get_distribution('gplaycli').version, sys.version.split()[0])
except DistributionNotFound:
	__version__ = 'unknown: gplaycli not installed (version in setup.py)'

logger  = logging.getLogger(__name__)  # default level is WARNING
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(handler)
logger.propagate = False


class ERRORS(enum.IntEnum):
	"""
	Contains constant errors for Gplaycli
	"""
	SUCCESS = 0
	TOKEN_DISPENSER_AUTH_ERROR = 5
	TOKEN_DISPENSER_SERVER_ERROR = 6
	KEYRING_NOT_INSTALLED = 10
	CANNOT_LOGIN_GPLAY = 15


class GPlaycli:
	"""
	Object which handles Google Play connection
	search and download.
	GPlaycli can be used as an API with parameters
	token_enable, token_url, config and with methods
	retrieve_token(), connect(),
	download(), search().
	"""

	def __init__(self, args=None, config_file=None):
		# no config file given, look for one
		if config_file is None:
			# default local user configs
			cred_paths_list = [
				'gplaycli.conf',
				os.path.expanduser("~") + '/.config/gplaycli/gplaycli.conf',
				'/etc/gplaycli/gplaycli.conf'
			]
			config_file = None
			for filepath in cred_paths_list:
				if os.path.isfile(filepath):
					config_file = filepath
					break
			if config_file is None:
				logger.warn("No configuration file found at %s, using default values" % cred_paths_list)

		self.api 			= None
		self.token_passed 	= False


		config = configparser.ConfigParser()
		if config_file:
			config.read(config_file)
		self.gmail_address      = config.get('Credentials', 'gmail_address', fallback=None)
		self.gmail_password		= config.get('Credentials', 'gmail_password', fallback=None)
		self.token_enable 		= config.getboolean('Credentials', 'token', fallback=True)
		self.token_url 			= config.get('Credentials', 'token_url', fallback='https://matlink.fr/token/email/gsfid')
		self.keyring_service    = config.get('Credentials', 'keyring_service', fallback=None)

		self.tokencachefile 	= os.path.expanduser(config.get("Cache", "token", fallback="token.cache"))
		self.yes 				= config.getboolean('Misc', 'accept_all', fallback=False)
		self.verbose 			= config.getboolean('Misc', 'verbose', fallback=False)
		self.append_version 	= config.getboolean('Misc', 'append_version', fallback=False)
		self.progress_bar 		= config.getboolean('Misc', 'progress', fallback=False)
		self.logging_enable 	= config.getboolean('Misc', 'enable_logging', fallback=False)
		self.addfiles_enable 	= config.getboolean('Misc', 'enable_addfiles', fallback=False)
		self.device_codename 	= config.get('Device', 'codename', fallback='bacon')
		self.locale 			= config.get("Locale", "locale", fallback="en_GB")
		self.timezone 			= config.get("Locale", "timezone", fallback="CEST")

		if not args: return

		# if args are passed, override defaults
		if args.yes is not None:
			self.yes = args.yes

		if args.verbose is not None:
			self.verbose = args.verbose

		if self.verbose:
			logger.setLevel(logging.INFO)
		logger.info('GPlayCli version %s', __version__)
		logger.info('Configuration file is %s', config_file)

		if args.append_version is not None:
			self.append_version = args.append_version

		if args.progress is not None:
			self.progress_bar = args.progress

		if args.update is not None:
			self.download_folder = args.update

		if args.log is not None:
			self.logging_enable = args.log

		if args.device_codename is not None:
			self.device_codename = args.device_codename
		logger.info('Device is %s', self.device_codename)

		if args.additional_files is not None:
			self.addfiles_enable = args.additional_files

		if args.token is not None:
			self.token_enable = args.token
		if self.token_enable is not None:
			if args.token_url is not None:
				self.token_url = args.token_url
			if (args.token_str is not None) and (args.gsfid is not None):
				self.token = args.token_str
				self.gsfid = args.gsfid
				self.token_passed = True
			elif args.token_str is None and args.gsfid is None:
				pass
			else:
				raise TypeError("Token string and GSFID have to be passed at the same time.")

		if self.logging_enable:
			self.success_logfile = "apps_downloaded.log"
			self.failed_logfile  = "apps_failed.log"
			self.unavail_logfile = "apps_not_available.log"

	########## Public methods ##########

	def retrieve_token(self, force_new=False):
		"""
		Return a token. If a cached token exists,
		it will be used. Else, or if force_new=True,
		a new token is fetched from the token-dispenser
		server located at self.token_url.
		"""
		self.token, self.gsfid, self.device = self.get_cached_token()
		if (self.token is not None and not force_new and self.device == self.device_codename):
			logger.info("Using cached token.")
			return

		logger.info("Retrieving token ...")
		url = '/'.join([self.token_url, self.device_codename])
		logger.info("Token URL is %s", url)
		response = requests.get(url)

		if response.text == 'Auth error':
			logger.error('Token dispenser auth error, probably too many connections')
			sys.exit(ERRORS.TOKEN_DISPENSER_AUTH_ERROR)

		elif response.text == "Server error":
			logger.error('Token dispenser server error')
			sys.exit(ERRORS.TOKEN_DISPENSER_SERVER_ERROR)

		elif len(response.text) != 88: # other kinds of errors
			logger.error('Unknown error: %s', response.text)
			sys.exit(ERRORS.TOKEN_DISPENSER_SERVER_ERROR)

		self.token, self.gsfid = response.text.split(" ")
		logger.info("Token: %s", self.token)
		logger.info("GSFId: %s", self.gsfid)
		self.write_cached_token(self.token, self.gsfid, self.device_codename)

	@hooks.connected
	def download(self, pkg_todownload):
		"""
		Download apks from the pkg_todownload list

		pkg_todownload -- list either of app names or
		of tuple of app names and filepath to write them

		Example: ['org.mozilla.focus','org.mozilla.firefox'] or
				 [('org.mozilla.focus', 'org.mozilla.focus.apk'),
				  ('org.mozilla.firefox', 'download/org.mozilla.firefox.apk')]
		"""
		success_downloads = []
		failed_downloads  = []
		unavail_downloads = []

		# case where no filenames have been provided
		for index, pkg in enumerate(pkg_todownload):
			if isinstance(pkg, str):
				pkg_todownload[index] = [pkg, None]
			# remove whitespaces before and after package name
			pkg_todownload[index][0] = pkg_todownload[index][0].strip()

		# Check for download folder
		download_folder = self.download_folder
		if not os.path.isdir(download_folder):
			os.makedirs(download_folder, exist_ok=True)

		# BulkDetails requires only one HTTP request
		# Get APK info from store
		details = list()
		for pkg in pkg_todownload:
			try:
				detail = self.api.details(pkg[0])
				details.append(detail)
			except RequestError as request_error:
				failed_downloads.append((pkg, request_error))

		if any([d is None for d in details]):
			logger.info("Token has expired while downloading. Retrieving a new one.")
			self.refresh_token()
			details = self.api.bulkDetails([pkg[0] for pkg in pkg_todownload])

		for position, (detail, item) in enumerate(zip(details, pkg_todownload)):
			packagename, filename = item

			if filename is None:
				if self.append_version:
					filename = "%s-v.%s.apk" % (detail['docid'], detail['details']['appDetails']['versionString'])
				else:
					filename = "%s.apk" % detail['docid']

			logger.info("%s / %s %s", 1+position, len(pkg_todownload), packagename)

			# Download
			try:
				if detail['offer'][0]['checkoutFlowRequired']:
					method = self.api.delivery
				else:
					method = self.api.download
				data_iter = method(packagename, expansion_files=self.addfiles_enable)
				success_downloads.append(packagename)
			except IndexError as exc:
				logger.error("Error while downloading %s : this package does not exist, "
							 "try to search it via --search before",
							 packagename)
				unavail_downloads.append((item, exc))
				continue
			except Exception as exc:
				logger.error("Error while downloading %s : %s", packagename, exc)
				failed_downloads.append((item, exc))
				continue

			filepath = os.path.join(download_folder, filename)

			#if file exists, continue
			if self.append_version and os.path.isfile(filepath):
				logger.info("File %s already exists, skipping.", filename)
				continue

			additional_data = data_iter['additionalData']
			total_size = int(data_iter['file']['total_size'])
			chunk_size = int(data_iter['file']['chunk_size'])
			try:
				with open(filepath, "wb") as fbuffer:
					bar = util.progressbar(expected_size=total_size, hide=not self.progress_bar)
					for index, chunk in enumerate(data_iter['file']['data']):
						fbuffer.write(chunk)
						bar.show(index * chunk_size)
					bar.done()
				if additional_data:
					for obb_file in additional_data:
						obb_filename = "%s.%s.%s.obb" % (obb_file["type"], obb_file["versionCode"], data_iter["docId"])
						obb_filename = os.path.join(download_folder, obb_filename)
						obb_total_size = int(obb_file['file']['total_size'])
						obb_chunk_size = int(obb_file['file']['chunk_size'])
						with open(obb_filename, "wb") as fbuffer:
							bar = util.progressbar(expected_size=obb_total_size, hide=not self.progress_bar)
							for index, chunk in enumerate(obb_file["file"]["data"]):
								fbuffer.write(chunk)
								bar.show(index * obb_chunk_size)
							bar.done()
			except IOError as exc:
				logger.error("Error while writing %s : %s", packagename, exc)
				failed_downloads.append((item, exc))

		success_items = set(success_downloads)
		failed_items  = set([item[0] for item, error in failed_downloads])
		unavail_items = set([item[0] for item, error in unavail_downloads])
		to_download_items = set([item[0] for item in pkg_todownload])

		self.write_logfiles(success_items, failed_items, unavail_items)
		self.print_failed(failed_downloads + unavail_downloads)
		return to_download_items - failed_items

	@hooks.connected
	def search(self, search_string, free_only=True, include_headers=True):
		"""
		Search the given string search_string on the Play Store.

		search_string   -- the string to search on the Play Store
		free_only       -- True if only costless apps should be searched for
		include_headers -- True if the result table should show column names
		"""
		try:
			results = self.api.search(search_string)
		except IndexError:
			results = []
		if not results:
			logger.info("No result")
			return
		all_results = []
		if include_headers:
			# Name of the columns
			col_names = ["Title", "Creator", "Size", "Downloads", "Last Update", "AppID", "Version", "Rating"]
			all_results.append(col_names)
		# Compute results values
		for doc in results:
			for cluster in doc["child"]:
				for app in cluster["child"]:
					# skip that app if it not free
					# or if it's beta (pre-registration)
					if ('offer' not in app  # beta apps (pre-registration)
							or free_only
							and app['offer'][0]['checkoutFlowRequired']  # not free to download
						):
						continue
					details = app['details']['appDetails']
					detail = [app['title'],
							  app['creator'],
							  util.sizeof_fmt(int(details['installationSize']))
							  if int(details['installationSize']) > 0 else 'N/A',
							  details['numDownloads'],
							  details['uploadDate'],
							  app['docid'],
							  details['versionCode'],
							  "%.2f" % app["aggregateRating"]["starRating"]
							  ]
					all_results.append(detail)

		# Print a nice table
		col_width = []
		for column_indice in range(len(all_results[0])):
			col_length = max([len("%s" % row[column_indice]) for row in all_results])
			col_width.append(col_length + 2)

		for result in all_results:
			for indice, item in enumerate(result):
				out = "".join(str(item).strip().ljust(col_width[indice]))
				try:
					print(out, end='')
				except UnicodeEncodeError:
					out = out.encode('utf-8', errors='replace')
					print(out, end='')
			print()
		return all_results

	########## End public methods ##########

	########## Internal methods ##########

	def connect(self):
		"""
		Connect GplayCli to the Google Play API.
		If self.token_enable=True, the token from
		self.retrieve_token is used. Else, classical
		credentials are used. They might be stored
		into the keyring if the keyring package
		is installed.
		"""
		self.api = GooglePlayAPI(locale=self.locale, timezone=self.timezone, device_codename=self.device_codename)
		if self.token_enable:
			self.retrieve_token()
			return self.connect_token()
		else:
			return self.connect_credentials()

	def connect_token(self):
		if self.token_passed:
			logger.info("Using passed token to connect to API")
		else:
			logger.info("Using auto retrieved token to connect to API")
		try:
			self.api.login(authSubToken=self.token, gsfId=int(self.gsfid, 16))
		except (ValueError, IndexError, LoginError, DecodeError, SystemError, RequestError):
			logger.info("Token has expired or is invalid. Retrieving a new one...")
			self.retrieve_token(force_new=True)
			self.connect()
		return True, None

	def connect_credentials(self):
		logger.info("Using credentials to connect to API")
		if self.gmail_password:
			logger.info("Using plaintext password")
			password = self.gmail_password
		elif self.keyring_service and HAVE_KEYRING:
			password = keyring.get_password(self.keyring_service, self.gmail_address)
		elif self.keyring_service and not HAVE_KEYRING:
			logger.error("You asked for keyring service but keyring package is not installed")
			return False, ERRORS.KEYRING_NOT_INSTALLED
		try:
			self.api.login(email=self.gmail_address, password=password)
		except LoginError as e:
			logger.error("Bad authentication, login or password incorrect (%s)", e)
			return False, ERRORS.CANNOT_LOGIN_GPLAY
		return True, None


	def get_cached_token(self):
		"""
		Retrieve a cached token,  gsfid and device if exist.
		Otherwise return None.
		"""
		try:
			cache_dic = json.loads(open(self.tokencachefile).read())
			token = cache_dic['token']
			gsfid = cache_dic['gsfid']
			device = cache_dic['device']
		except (IOError, ValueError):  # cache file does not exists or is corrupted
			token = None
			gsfid = None
			device = None
			logger.error('Cache file does not exists or is corrupted')
		return token, gsfid, device

	def write_cached_token(self, token, gsfid, device):
		"""
		Write the given token, gsfid and device
		to the self.tokencachefile file.
		Path and file are created if missing.
		"""
		cachedir = os.path.dirname(self.tokencachefile)
		if not cachedir:
			cachedir = os.getcwd()
		# creates cachedir if not exists
		if not os.path.exists(cachedir):
			os.makedirs(cachedir, exist_ok=True)
		with open(self.tokencachefile, 'w') as tcf:
			tcf.write(json.dumps({'token' : token,
								  'gsfid' : gsfid,
								  'device' : device}))

	def prepare_analyse_apks(self):
		"""
		Gather apks to further check for update
		"""
		list_of_apks = util.list_folder_apks(self.download_folder)
		if not list_of_apks:
			return
		logger.info("Checking apks ...")
		to_update = self.analyse_local_apks(list_of_apks, self.download_folder)
		return self.prepare_download_updates(to_update)

	@hooks.connected
	def analyse_local_apks(self, list_of_apks, download_folder):
		"""
		Analyse apks in the list list_of_apks
		to check for updates and download updates
		in the download_folder folder.
		"""
		list_apks_to_update = []
		package_bunch = []
		version_codes = []
		unavail_items = []
		UNAVAIL = "This app is not available in the Play Store"
		for filename in list_of_apks:
			filepath = os.path.join(download_folder, filename)
			logger.info("Analyzing %s", filepath)
			apk = APK(filepath)
			packagename = apk.package
			package_bunch.append(packagename)
			version_codes.append(util.vcode(apk.version_code))

		# BulkDetails requires only one HTTP request
		# Get APK info from store
		details = self.api.bulkDetails(package_bunch)
		for detail, packagename, filename, apk_version_code in zip(details, package_bunch, list_of_apks, version_codes):
			# this app is not in the play store
			if not detail:
				unavail_items.append(((packagename, filename), UNAVAIL))
				continue
			store_version_code = detail['details']['appDetails']['versionCode']

			# Compare
			if apk_version_code < store_version_code:
				# Add to the download list
				list_apks_to_update.append([packagename, filename, apk_version_code, store_version_code])

		self.write_logfiles(None, None, [item[0][0] for item in unavail_items])
		self.print_failed(unavail_items)

		return list_apks_to_update

	def prepare_download_updates(self, list_apks_to_update):
		"""
		Ask confirmation before updating apks
		"""
		if not list_apks_to_update:
			print("Everything is up to date !")
			return False

		pkg_todownload = []

		# Ask confirmation before downloading
		print("The following applications will be updated :")
		for packagename, filename, apk_version_code, store_version_code in list_apks_to_update:
			print("%s Version : %s -> %s" % (filename, apk_version_code, store_version_code))
			pkg_todownload.append([packagename, filename])

		if not self.yes:
			print("Do you agree?")
			return_value = input('y/n ?')

		if self.yes or return_value == 'y':
			logger.info("Downloading ...")
			downloaded_packages = self.download(pkg_todownload)
			return_string = ' '.join(downloaded_packages)
			print("Updated: %s" % return_string)
		return True

	@staticmethod
	def print_failed(failed_downloads):
		"""
		Print/log failed downloads from failed_downloads
		"""
		# Info message
		if not failed_downloads:
			return
		else:
			message = "A few packages could not be downloaded :\n"
			for pkg, exception in failed_downloads:
				package_name, filename = pkg
				if filename is not None:
					message += "%s : %s\n" % (filename, package_name)
				else:
					message += "%s\n" % package_name
				message += "%s\n" % exception
			logger.error(message)

	def write_logfiles(self, success, failed, unavail):
		"""
		Write success failed and unavail list to
		logfiles
		"""
		if not self.logging_enable:
			return
		for result, logfile in [(success, self.success_logfile), (failed, self.failed_logfile), (unavail, self.unavail_logfile)]:
			if not result:
				continue
			with open(logfile, 'w') as _buffer:
				for package in result:
					print(package, file=_buffer)

	########## End internal methods ##########


def main():
	"""
	Main function.
	Parse command line arguments
	"""
	parser = argparse.ArgumentParser(description="A Google Play Store Apk downloader and manager for command line")
	parser.add_argument('-V',  '--version',				help="Print version number and exit", action='store_true')
	parser.add_argument('-v',  '--verbose',				help="Be verbose", action='store_true')
	parser.add_argument('-s',  '--search',				help="Search the given string in Google Play Store", metavar="SEARCH")
	parser.add_argument('-d',  '--download',			help="Download the Apps that map given AppIDs", metavar="AppID", nargs="+")
	parser.add_argument('-y',  '--yes',					help="Say yes to all prompted questions", action='store_true')
	parser.add_argument('-l',  '--list',				help="List APKS in the given folder, with details", metavar="FOLDER")
	parser.add_argument('-P',  '--paid',				help="Also search for paid apps", action='store_true', default=False)
	parser.add_argument('-av', '--append-version',		help="Append versionstring to APKs when downloading", action='store_true')
	parser.add_argument('-a',  '--additional-files',	help="Enable the download of additional files", action='store_true', default=False)
	parser.add_argument('-F',  '--file',				help="Load packages to download from file, one package per line", metavar="FILE")
	parser.add_argument('-u',  '--update',				help="Update all APKs in a given folder", metavar="FOLDER")
	parser.add_argument('-f',  '--folder',				help="Where to put the downloaded Apks, only for -d command", metavar="FOLDER", nargs=1, default=['.'])
	parser.add_argument('-dc', '--device-codename',		help="The device codename to fake", choices=GooglePlayAPI.getDevicesCodenames(), metavar="DEVICE_CODENAME")
	parser.add_argument('-t',  '--token',				help="Instead of classical credentials, use the tokenize version", action='store_true', default=None)
	parser.add_argument('-tu', '--token-url',			help="Use the given tokendispenser URL to retrieve a token", metavar="TOKEN_URL")
	parser.add_argument('-ts', '--token-str',			help="Supply token string by yourself, need to supply GSF_ID at the same time", metavar="TOKEN_STR")
	parser.add_argument('-g',  '--gsfid',				help="Supply GSF_ID by yourself, need to supply token string at the same time", metavar="GSF_ID")
	parser.add_argument('-c',  '--config',				help="Use a different config file than gplaycli.conf", metavar="CONF_FILE", nargs=1)
	parser.add_argument('-p',  '--progress',			help="Prompt a progress bar while downloading packages", action='store_true')
	parser.add_argument('-L',  '--log',					help="Enable logging of apps status in separate logging files", action='store_true', default=False)

	if len(sys.argv) < 2:
		sys.argv.append("-h")

	args = parser.parse_args()

	if args.version:
		print(__version__)
		return

	cli = GPlaycli(args, args.config)

	if args.list:
		print(util.list_folder_apks(args.list))

	if args.update:
		cli.prepare_analyse_apks()
		return

	if args.search:
		cli.verbose = True
		cli.search(args.search, not args.paid)

	if args.file:
		args.download = util.load_from_file(args.file)

	if args.download is not None:
		if args.folder is not None:
			cli.download_folder = args.folder[0]
		cli.download(args.download)


if __name__ == '__main__':
	main()
