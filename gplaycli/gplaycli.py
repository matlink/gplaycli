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

import sys
import os
import logging
import argparse
import configparser
import warnings
import json
import time

from enum import IntEnum

import requests

from gpapi.googleplay import GooglePlayAPI
from gpapi.googleplay import LoginError
from gpapi.googleplay import RequestError
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

logger = logging.getLogger(__name__)  # default level is WARNING


class ERRORS(IntEnum):
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
			tmp_list = list(cred_paths_list)
			while not os.path.isfile(tmp_list[0]):
				tmp_list.pop(0)
				if not tmp_list:
					raise OSError("No configuration file found at %s" % cred_paths_list)
			config_file = tmp_list[0]

		default_values = {}
		self.configparser = configparser.ConfigParser(default_values)
		self.configparser.read(config_file)
		self.creds = {key: value for key, value in self.configparser.items("Credentials")}

		self.tokencachefile = os.path.expanduser(
			self.configparser.get("Cache", "token", fallback="token.cache"))
		self.api = None
		self.token_passed = False
		self.locale = self.configparser.get("Locale", "locale", fallback="en_GB")
		self.timezone = self.configparser.get("Locale", "timezone", fallback="CEST")

		# default settings, ie for API calls
		if args is None:
			self.yes = False
			self.verbose = False
			self.append_version = False
			self.progress_bar = False
			self.logging_enable = False
			self.device_codename = 'bacon'
			self.addfiles_enable = False

		# if args are passed
		else:
			self.yes = args.yes_to_all
			self.verbose = args.verbose
			if self.verbose:
				logger.setLevel(logging.INFO)
				handler = logging.StreamHandler()
				formatter = logging.Formatter("[%(levelname)s] %(message)s")
				handler.setFormatter(formatter)
				logger.addHandler(handler)
				logger.propagate = False
			logger.info('GPlayCli version %s', __version__)
			logger.info('Configuration file is %s', config_file)
			self.append_version = args.append_version
			self.progress_bar = args.progress_bar
			self.set_download_folder(args.update_folder)
			self.logging_enable = args.logging_enable
			self.device_codename = args.device_codename
			logger.info('Device is %s', self.device_codename)
			self.addfiles_enable = args.addfiles_enable
			if args.locale is not None:
				self.locale = args.locale
			if args.timezone is not None:
				self.timezone = args.timezone

			if args.token_enable is None:
				self.token_enable = self.configparser.getboolean('Credentials', 'token')
			else:
				self.token_enable = args.token_enable
			if self.token_enable:
				if args.token_url is None:
					self.token_url = self.configparser.get('Credentials', 'token_url')
				else:
					self.token_url = args.token_url

				if (args.token_str is None) and (args.gsf_id is None):
					self.token, self.gsfid = self.retrieve_token()
				elif (args.token_str is not None) and (args.gsf_id is not None):
					self.token = args.token_str
					self.gsfid = args.gsf_id
					self.token_passed = True
				else:  # Either args.token_str or args.gsf_id is None
					raise TypeError("Token string and GSFID have to be passed at the same time.")

			if self.logging_enable:
				self.success_logfile = "apps_downloaded.log"
				self.failed_logfile = "apps_failed.log"
				self.unavail_logfile = "apps_not_available.log"

	########## Public methods ##########

	def retrieve_token(self, force_new=False):
		"""
		Return a token. If a cached token exists,
		it will be used. Else, or if force_new=True,
		a new token is fetched from the token-dispenser
		server located at self.token_url.
		"""
		token, gsfid, device = self.get_cached_token()
		self.retrieve_time = time.time()
		if (token is not None
				and not force_new
				and device == self.device_codename):
			logger.info("Using cached token.")
			return token, gsfid
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
			logger.error('Unknowned error: %s', response.text)
			sys.exit(ERRORS.TOKEN_DISPENSER_SERVER_ERROR)
		token, gsfid = response.text.split(" ")
		logger.info("Token: %s", token)
		logger.info("GSFId: %s", gsfid)
		self.token = token
		self.gsfid = gsfid
		self.write_cached_token(token, gsfid, self.device_codename)
		return token, gsfid

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
		failed_downloads = []
		unavail_downloads = []

		# case where no filenames have been provided
		for index, pkg in enumerate(pkg_todownload):
			if isinstance(pkg, str):
				pkg_todownload[index] = [pkg, None]
			# remove whitespaces before and after package name
			pkg_todownload[index][0] = pkg_todownload[index][0].strip('\r\n ')

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
		position = 1
		for detail, item in zip(details, pkg_todownload):
			packagename, filename = item

			if filename is None:
				if self.append_version:
					filename = detail['docId']+ "-v." + detail['versionString'] + ".apk"
				else:
					filename = detail['docId']+ ".apk"

			logger.info("%s / %s %s", position, len(pkg_todownload), packagename)

			# Check for download folder
			download_folder = self.download_folder
			if not os.path.isdir(download_folder):
				os.makedirs(download_folder, exist_ok=True)

			# Download
			try:
				if detail['offer'][0]['checkoutFlowRequired']:
					method = self.api.delivery
				else:
					method = self.api.download
				data_iter = method(packagename,
								   expansion_files=self.addfiles_enable)
				success_downloads.append(packagename)
			except IndexError as exc:
				logger.error("Error while downloading %s : this package does not exist, "
							 "try to search it via --search before",
							 packagename)
				unavail_downloads.append((item, exc))
			except Exception as exc:
				logger.error("Error while downloading %s : %s", packagename, exc)
				failed_downloads.append((item, exc))
			else:
				filepath = os.path.join(download_folder, filename)

				#if file exists, continue
				if self.append_version and os.path.isfile(filepath):
					logger.info("File %s already exists, skipping.", filename)
					position += 1
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
							obb_filename = "%s.%s.%s.obb" % (obb_file["type"],
															 obb_file["versionCode"],
															 data_iter["docId"])
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
			position += 1

		success_items = set(success_downloads)
		failed_items = set([item[0] for item, error in failed_downloads])
		unavail_items = set([item[0] for item, error in unavail_downloads])
		to_download_items = set([item[0] for item in pkg_todownload])

		if self.logging_enable:
			self.write_logfiles(success_items, failed_items, unavail_items)

		self.print_failed(failed_downloads + unavail_downloads)
		return to_download_items - failed_items

	@hooks.connected
	def search(self, search_string, nb_results, free_only=True, include_headers=True):
		"""
		Search the given string search_string on the Play Store.

		search_string   -- the string to search on the Play Store
		nb_results      -- the number of results to print
		free_only       -- True if only costless apps should be searched for
		include_headers -- True if the result table should show column names
		"""
		try:
			results = self.api.search(search_string, nb_result=nb_results)
		except IndexError:
			results = []
		if not results:
			logger.info("No result")
			return
		all_results = []
		if include_headers:
			# Name of the columns
			col_names = ["Title",
						 "Creator",
						 "Size",
						 "Downloads",
						 "Last Update",
						 "AppID",
						 "Version",
						 "Rating"
						 ]
			all_results.append(col_names)
		# Compute results values
		for result in results:
			# skip that app if it not free
			# or if it's beta (pre-registration)
			if (len(result['offer']) == 0  # beta apps (pre-registration)
					or free_only
					and result['offer'][0]['checkoutFlowRequired']  # not free to download
				):
				continue
			detail = [result['title'],
					  result['author'],
					  util.sizeof_fmt(result['installationSize'])
					  if result['installationSize'] > 0 else 'N/A',
					  result['numDownloads'],
					  result['uploadDate'],
					  result['docId'],
					  result['versionCode'],
					  "%.2f" % result["aggregateRating"]["starRating"]
					  ]
			if len(all_results) < int(nb_results) + 1:
				all_results.append(detail)

		if self.verbose:
			# Print a nice table
			col_width = []
			for column_indice in range(len(all_results[0])):
				col_length = max([len("%s" % row[column_indice]) for row in all_results])
				col_width.append(col_length + 2)

			for result in all_results:
				for indice, item in enumerate(result):
					out = str(item)
					out = out.strip()
					out = out.ljust(col_width[indice])
					out = "".join(out)
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
		error = None
		email = None
		password = None
		authsub_token = None
		gsfid = None
		if self.token_enable is False:
			logger.info("Using credentials to connect to API")
			email = self.creds["gmail_address"]
			if self.creds["gmail_password"]:
				logger.info("Using plaintext password")
				password = self.creds["gmail_password"]
			elif self.creds["keyring_service"] and HAVE_KEYRING is True:
				password = keyring.get_password(self.creds["keyring_service"], email)
			elif self.creds["keyring_service"] and HAVE_KEYRING is False:
				logger.error("You asked for keyring service but keyring package is not installed")
				sys.exit(ERRORS.KEYRING_NOT_INSTALLED)
		else:
			if self.token_passed:
				logger.info("Using passed token to connect to API")
			else:
				logger.info("Using auto retrieved token to connect to API")
			authsub_token = self.token
			gsfid = int(self.gsfid, 16)
		with warnings.catch_warnings():
			warnings.simplefilter('error')
			try:
				if self.token_enable:
					now = time.time()
					if now - self.retrieve_time < 5:
						# Need to wait a bit before loging in with this token
						time.sleep(5)
				self.api.login(email=email,
							   password=password,
							   authSubToken=authsub_token,
							   gsfId=gsfid)
			except LoginError as login_error:
				logger.error("Bad authentication, login or password incorrect (%s)", login_error)
				return False, ERRORS.CANNOT_LOGIN_GPLAY
			# invalid token or expired
			except (ValueError, IndexError, LoginError, DecodeError, SystemError):
				logger.info("Token has expired or is invalid. Retrieving a new one...")
				self.refresh_token()
		success = True
		return success, error

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
			logger.error('cache file does not exists or is corrupted')
		return token, gsfid, device

	def write_cached_token(self, token, gsfid, device):
		"""
		Write the given token, gsfid and device
		to the self.tokencachefile file.
		Path and file are created if missing.
		"""
		try:
			# creates cachedir if not exists
			cachedir = os.path.dirname(self.tokencachefile)
			if not os.path.exists(cachedir):
				os.makedirs(cachedir, exist_ok=True)
			with open(self.tokencachefile, 'w') as tcf:
				tcf.write(json.dumps({'token' : token,
									  'gsfid' : gsfid,
									  'device' : device}))
		except IOError as io_error:
			err_str = "Failed to write token to cache file: %s %s" % (
				self.tokencachefile, io_error.strerror)
			logger.error(err_str)
			raise IOError(err_str)

	def set_download_folder(self, folder):
		"""
		Set the download folder for apk
		to folder.
		"""
		self.download_folder = folder

	def refresh_token(self):
		"""
		Get a new token from token-dispenser instance
		and re-connect to the play-store.
		"""
		self.retrieve_token(force_new=True)
		self.api.login(authSubToken=self.token, gsfId=int(self.gsfid, 16))

	def prepare_analyse_apks(self):
		"""
		Gather apks to further check for update
		"""
		download_folder = self.download_folder
		list_of_apks = util.list_folder_apks(download_folder)
		if list_of_apks:
			logger.info("Checking apks ...")
			to_update = self.analyse_local_apks(list_of_apks, download_folder)
			self.prepare_download_updates(to_update)

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
		for detail, packagename, filename, apk_version_code in zip(details,
																   package_bunch,
																   list_of_apks,
																   version_codes):
			# this app is not in the play store
			if not detail:
				unavail_items.append(((packagename, filename), UNAVAIL))
				continue
			store_version_code = detail['versionCode']

			# Compare
			if apk_version_code < store_version_code:
				# Add to the download list
				list_apks_to_update.append([packagename,
											filename,
											apk_version_code,
											store_version_code])

		if self.logging_enable:
			self.write_logfiles(None, None, [item[0][0] for item in unavail_items])
		self.print_failed(unavail_items)

		return list_apks_to_update

	def prepare_download_updates(self, list_apks_to_update):
		"""
		Ask confirmation before updating apks
		"""
		if list_apks_to_update:
			pkg_todownload = []

			# Ask confirmation before downloading
			message = "The following applications will be updated :"
			for packagename, filename, apk_version_code, store_version_code in list_apks_to_update:
				message += "\n%s Version : %s -> %s" % (filename,
														apk_version_code,
														store_version_code)
				pkg_todownload.append([packagename, filename])
			message += "\n"
			print(message)
			if not self.yes:
				print("\nDo you agree?")
				return_value = input('y/n ?')

			if self.yes or return_value == 'y':
				logger.info("Downloading ...")
				downloaded_packages = self.download(pkg_todownload)
				return_string = ' '.join(downloaded_packages)
				print("Updated: " + return_string)
		else:
			print("Everything is up to date !")
			sys.exit(ERRORS.SUCCESS)

	@staticmethod
	def print_failed(failed_downloads):
		"""
		Print/log failed downloads from failed_downloads
		"""
		# Info message
		if not failed_downloads:
			logger.info("Download complete")
		else:
			message = "A few packages could not be downloaded :"
			for pkg, exception in failed_downloads:
				package_name, filename = pkg
				if filename is not None:
					message += "\n%s : %s" % (filename, package_name)
				else:
					message += "\n%s" % package_name
				message += "\n%s\n" % exception
			logger.error(message)

	def write_logfiles(self, success, failed, unavail):
		"""
		Write success failed and unavail list to
		logfiles
		"""
		for result, logfile in [(success, self.success_logfile),
								(failed, self.failed_logfile),
								(unavail, self.unavail_logfile)
								]:
			if result:
				with open(logfile, 'w') as _buffer:
					for package in result:
						print(package, file=_buffer)

	########## End internal methods ##########


def main():
	"""
	Main function.
	Parse command line arguments
	"""
	parser = argparse.ArgumentParser(description="A Google Play Store Apk downloader"
												 " and manager for command line")
	parser.add_argument('-V', '--version', action='store_true', dest='version',
						help="Print version number and exit")
	parser.add_argument('-y', '--yes', action='store_true', dest='yes_to_all',
						help="Say yes to all prompted questions")
	parser.add_argument('-l', '--list', action='store', dest='list', metavar="FOLDER",
						type=str,
						help="List APKS in the given folder, with details")
	parser.add_argument('-s', '--search', action='store', dest='search_string', metavar="SEARCH",
						type=str,
						help="Search the given string in Google Play Store")
	parser.add_argument('-P', '--paid', action='store_true', dest='paid',
						default=False,
						help="Also search for paid apps")
	parser.add_argument('-n', '--number', action='store', dest='number_results',
						metavar="NUMBER", type=int,
						help="For the search option, returns the given "
							 "number of matching applications")
	parser.add_argument('-d', '--download', action='store', dest='packages_to_download',
						metavar="AppID", nargs="+", type=str,
						help="Download the Apps that map given AppIDs")
	parser.add_argument('-av', '--append-version', action='store_true', dest='append_version',
						help="Append versionstring to APKs when downloading")
	parser.add_argument('-a', '--additional-files', action='store_true', dest='addfiles_enable',
						default=False,
						help="Enable the download of additional files")
	parser.add_argument('-F', '--file', action='store', dest='load_from_file', metavar="FILE",
						type=str,
						help="Load packages to download from file, "
							 "one package per line")
	parser.add_argument('-u', '--update', action='store', dest='update_folder', metavar="FOLDER",
						type=str,
						help="Update all APKs in a given folder")
	parser.add_argument('-f', '--folder', action='store', dest='dest_folder',
						metavar="FOLDER", nargs=1, type=str, default=".",
						help="Where to put the downloaded Apks, only for -d command")
	parser.add_argument('-dc', '--device-codename', action='store', dest='device_codename',
						metavar="DEVICE_CODENAME",
						type=str, default="bacon",
						help="The device codename to fake",
						choices=GooglePlayAPI.getDevicesCodenames())
	parser.add_argument('-ts', '--token-str', action='store', dest='token_str',
						metavar="TOKEN_STR", type=str, default=None,
						help="Supply token string by yourself, "
							 "need to supply GSF_ID at the same time")
	parser.add_argument('-g', '--gsf-id', action='store', dest='gsf_id', metavar="GSF_ID",
						type=str, default=None,
						help="Supply GSF_ID by yourself, "
							 "need to supply token string at the same time")
	parser.add_argument('-t', '--token', action='store_true', dest='token_enable', default=None,
						help="Instead of classical credentials, use the tokenize version")
	parser.add_argument('-tu', '--token-url', action='store', dest='token_url',
						metavar="TOKEN_URL", type=str, default=None,
						help="Use the given tokendispenser URL to retrieve a token")
	parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
						help="Be verbose")
	parser.add_argument('-c', '--config', action='store', dest='config', metavar="CONF_FILE",
						nargs=1, type=str, default=None,
						help="Use a different config file than gplaycli.conf")
	parser.add_argument('-p', '--progress', action='store_true', dest='progress_bar',
						help="Prompt a progress bar while downloading packages")
	parser.add_argument('-L', '--log', action='store_true', dest='logging_enable', default=False,
						help="Enable logging of apps status. Downloaded, failed,"
							 "not available apps will be written in separate logging files")
	parser.add_argument('-lo', '--locale', action='store', dest='locale',
						type=str, metavar="LOCALE",
						help="The locale to use. Ex: en_GB")
	parser.add_argument('-tz', '--timezone', action='store', dest='timezone',
						type=str, metavar="TIMEZONE",
						help="The timezone to use. Ex: CEST")

	if len(sys.argv) < 2:
		sys.argv.append("-h")

	args = parser.parse_args()

	if args.version:
		print(__version__)
		return

	cli = GPlaycli(args, args.config)

	if args.list:
		print(util.list_folder_apks(args.list))

	if args.update_folder:
		cli.prepare_analyse_apks()

	if args.search_string:
		cli.verbose = True
		nb_results = 10
		if args.number_results:
			nb_results = args.number_results
		cli.search(args.search_string, nb_results, not args.paid)

	if args.load_from_file:
		args.packages_to_download = util.load_from_file(args.load_from_file)

	if args.packages_to_download is not None:
		if args.dest_folder is not None:
			cli.set_download_folder(args.dest_folder[0])
		cli.download(args.packages_to_download)


if __name__ == '__main__':
	main()
