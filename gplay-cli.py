#! /usr/bin/python2
# -*- coding: utf-8 -*-
"""
GPlay-Cli 
Copyleft (C) 2015 Matlink
Hardly based on GooglePlayDownloader https://codingteam.net/project/googleplaydownloader
Copyright (C) 2013   Tuxicoman

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.
You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys, os, argparse
from ext_libs.googleplay_api.googleplay import GooglePlayAPI #GooglePlayAPI
from ext_libs.googleplay_api.googleplay import LoginError
from ext_libs.androguard.core.bytecodes import apk as androguard_apk #Androguard

class GPlaycli(object):
	def __init__(self):
		self.config = {
			"gmail_password": "jesuischarlie", 
			"android_ID": "3f07fa136be3e63d", 
			"gmail_address": "googleplay@jesuislibre.net",
			"language": "fr_FR"
		}
		self.yes = False
		self.verbose = False

	def set_download_folder(self,folder):
		self.config["download_folder_path"] = folder

	def connect_to_googleplay_api(self):
	    AUTH_TOKEN = None

	    api = GooglePlayAPI(androidId=self.config["android_ID"], lang=self.config["language"])
	    try :
	      api.login(self.config["gmail_address"], self.config["gmail_password"], AUTH_TOKEN)
	    except LoginError, exc:
	      print exc.value
	      success = False
	    else:
	      self.playstore_api = api
	      success = True

	    return success

	def prepare_analyse_apks(self):
	    download_folder_path = self.config["download_folder_path"]
	    list_of_apks = [filename for filename in os.listdir(download_folder_path) if os.path.splitext(filename)[1] == ".apk"]
	    if len(list_of_apks) > 0:
	      if self.verbose:
	      	print "Checking apks ..."
	      self.analyse_local_apks(list_of_apks, self.playstore_api, download_folder_path, self.prepare_download_updates)

	def analyse_local_apks(self,list_of_apks, playstore_api, download_folder_path, return_function):
		list_apks_to_update = []
		for position, filename in enumerate(list_of_apks):
			filepath = os.path.join(download_folder_path, filename)
			a = androguard_apk.APK(filepath)
			apk_version_code = a.get_androidversion_code()
			packagename = a.get_package()
			if self.verbose:
				print "Analyzing %s" % packagename

			#Get APK info from store
			m =playstore_api.details(packagename)
			doc = m.docV2
			store_version_code = doc.details.appDetails.versionCode

			#Compare
			if apk_version_code != "" and int(apk_version_code) != int(store_version_code) and int(store_version_code) != 0:
			  #Add to the download list
			  list_apks_to_update.append([packagename, filename, int(apk_version_code), int(store_version_code)])

		return_function(list_apks_to_update)

	def prepare_download_updates(self, list_apks_to_update):
	    if len(list_apks_to_update) > 0:
	      list_of_packages_to_download = []

	      #Ask confirmation before downloading
	      message = u"The following applications will be updated :"
	      for packagename, filename, apk_version_code, store_version_code in list_apks_to_update :
	        message += u"\n%s Version : %s -> %s" % (filename ,apk_version_code, store_version_code)
	        list_of_packages_to_download.append([packagename, filename])
	      message += "\n\nDo you agree?"
	      print message 
	      if not self.yes:
	      	return_value = raw_input('y/n ?')

	      if self.yes or return_value == 'y':
	        if self.verbose:
	        	print "Downloading ..."
	        self.download_selection(self.playstore_api, list_of_packages_to_download, self.after_download)
	    else:
	    	print "Everything is up to date !"
	    	sys.exit(1)

	def download_selection(self,playstore_api, list_of_packages_to_download, return_function):
		failed_downloads = []
		for position, item in enumerate(list_of_packages_to_download):
			packagename, filename = item
			if self.verbose:
				print str(position+1)+"/"+str(len(list_of_packages_to_download)), packagename

			#Check for download folder
			download_folder_path = self.config["download_folder_path"]
			if not os.path.isdir(download_folder_path):
			  os.mkdir(download_folder_path)

			# Get the version code and the offer type from the app details
			m = playstore_api.details(packagename)
			doc = m.docV2
			title = doc.title
			vc = doc.details.appDetails.versionCode

			# Download
			try:
			  data = playstore_api.download(packagename, vc)
			except Exception as exc:
			  print "Error while downloading %s : %s" % (packagename, exc)
			  failed_downloads.append((item, exc))
			else:
			  if filename == None:
			    filename = packagename + ".apk"
			  filepath = os.path.join(download_folder_path,filename)

			  try:
			    open(filepath, "wb").write(data)
			  except IOError, exc:
			    print "Error while writing %s : %s" % (packagename, exc)
			    failed_downloads.append((item, exc))
		return_function(failed_downloads)
	def after_download(self, failed_downloads):
	    #Info message
	    if len(failed_downloads) == 0 :
	      message = "Download complete"
	    else:
	      message = "A few packages could not be downloaded :"
	      for item, exception in failed_downloads:
	        package_name, filename = item
	        if filename !=None :
	          message += "\n%s : %s" % (filename, package_name)
	        else:
	          message += "\n%s" % package_name
	        message += "\n%s\n" % exception

	def sizeof_fmt(self,num):
	  for x in ['bytes','KB','MB','GB','TB']:
	    if num < 1024.0:
	        return "%3.1f%s" % (num, x)
	    num /= 1024.0

	def search(self, results_list, search_string, nb_results):
		#Query results
		results = self.playstore_api.search(search_string, nb_results=nb_results).doc
		if len(results) > 0:
			results = results[0].child
		else:
			print "No result"
			return
		all_results = list()
		# Name of the columns
		col_names = ["Title","Creator","Size","Downloads","Last Update","AppID","Version","Rating"]
		all_results.append(col_names)
		# Compute results values
		for result in results:
			if result.offer[0].checkoutFlowRequired == False: #if Free to download
				l = [ result.title,
				result.creator,
				self.sizeof_fmt(result.details.appDetails.installationSize),
				result.details.appDetails.numDownloads,
				result.details.appDetails.uploadDate,
				result.docid,
				result.details.appDetails.versionCode,
				"%.2f" % result.aggregateRating.starRating
				]
			all_results.append(l)

		# Print a nice table
		col_width = list()
		for column_indice in range(len(all_results[0])):
			col_length = max([len(u"%s"%row[column_indice]) for row in all_results])
			col_width.append(col_length+2)

		for result in all_results:
			line = ""
			print "".join((u"%s"%item).ljust(col_width[indice]) for indice,item in enumerate(result))

	def download_packages(self,list_of_packages_to_download):
		self.download_selection(self.playstore_api, [(pkg,None) for pkg in list_of_packages_to_download], self.after_download)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="A Google Play Store Apk downloader and manager for command line")
	parser.add_argument('-y','--yes', action='store_true',dest='yes_to_all',help='Say yes to all prompted questions')
	parser.add_argument('-s','--search',action='store',dest='search_string',metavar="SEARCH",
		type=str,help="Search the given string into the Google Play Store")
	parser.add_argument('-n','--number',action='store',dest='number_results',metavar="NUMBER",
		type=str,help="For the search option, returns the given number of matching applications")
	parser.add_argument('-d','--download',action='store',dest='packages_to_download',metavar="AppID",nargs="+",
		type=str,help="Download the Apps that map given AppIDs")
	parser.add_argument('-u','--update',action='store',dest='update_folder',metavar="FOLDER",
		type=str,help="Update all the APKs in the given folder")
	parser.add_argument('-f','--folder',action='store',dest='dest_folder',metavar="FOLDER",nargs=1,
		type=str,default=".",help="Where to put the downloaded Apks, only for -d command")
	parser.add_argument('-v','--verbose', action='store_true',dest='verbose',help='Be verbose')
	if len(sys.argv)<2:
		sys.argv.append("-h")
	args = parser.parse_args()
	cli = GPlaycli()
	cli.yes = args.yes_to_all
	cli.verbose = args.verbose
	cli.set_download_folder(args.update_folder)
	cli.connect_to_googleplay_api()
	if args.update_folder:
		cli.prepare_analyse_apks()
	if args.search_string:
		nb_results = 10
		if args.number_results:
			nb_results=args.number_results
		cli.search(list(),args.search_string,nb_results)
	if args.packages_to_download!=None:
		if args.dest_folder!=None:
			cli.set_download_folder(args.dest_folder[0])
		cli.download_packages(args.packages_to_download)