#! /usr/bin/python2
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
import argparse
import ConfigParser
import time
import requests
from enum import IntEnum
from ext_libs.googleplay_api.googleplay import GooglePlayAPI  # GooglePlayAPI
from ext_libs.googleplay_api.googleplay import LoginError
from androguard.core.bytecodes import apk as androguard_apk  # Androguard
from google.protobuf.message import DecodeError
from pkg_resources import get_distribution, DistributionNotFound
try:
    import keyring
    HAVE_KEYRING = True
except ImportError:
    HAVE_KEYRING = False

import ext_libs.googleplay_api.googleplay

try:
    __version__ = '%s [Python%s] ' % (get_distribution('gplaycli').version, sys.version.split()[0])
except DistributionNotFound:
    __version__ = 'unknown: gplaycli not installed (version in setup.py)'


class ERRORS(IntEnum):
    OK = 0
    TOKEN_DISPENSER_AUTH_ERROR = 5
    TOKEN_DISPENSER_SERVER_ERROR = 6
    KEYRING_NOT_INSTALLED = 10
    CANNOT_LOGIN_GPLAY = 15

class GPlaycli(object):
    def __init__(self, args=None, credentials=None):
        # no config file given, look for one
        if credentials is None:
            # default local user configs
            cred_paths_list = [
                'gplaycli.conf',
                os.path.expanduser("~")+'/.config/gplaycli/gplaycli.conf',
                '/etc/gplaycli/gplaycli.conf'
            ]
            tmp_list = list(cred_paths_list)
            while not os.path.isfile(tmp_list[0]):
                tmp_list.pop(0)
                if len(tmp_list) == 0:
                    raise OSError("No configuration file found at %s" % cred_paths_list)
            credentials = tmp_list[0]

        default_values = {
            "retries": 10,
        }
        self.configparser = ConfigParser.ConfigParser(default_values)
        self.configparser.read(credentials)
        self.config = dict()
        for key, value in self.configparser.items("Credentials"):
            self.config[key] = value

        self.tokencachefile = os.path.expanduser( self.configparser.get("Cache", "token") )

        # default settings, ie for API calls
        if args is None:
            self.yes = False
            self.verbose = False
            self.progress_bar = False
            self.logging = False

        # if args are passed
        else:
            self.yes = args.yes_to_all
            self.verbose = args.verbose
            logging(self, 'GPlayCli version %s' % __version__)
            logging(self, 'Configuration file is %s' % credentials)
            self.progress_bar = args.progress_bar
            self.set_download_folder(args.update_folder)
            self.logging = args.enable_logging
            self.token = args.token
            self.retries = int(self.config["retries"])
            if self.token == True:
                self.token_url = args.token_url
            if self.token == False and 'token' in self.config and self.config['token'] == 'True':
                self.token = self.config['token']
                self.token_url = self.config['token_url']
            if str(self.token) == 'True':
                self.token = self.retrieve_token(self.token_url)

            if self.logging:
                self.success_logfile = "apps_downloaded.log"
                self.failed_logfile  = "apps_failed.log"
                self.unavail_logfile = "apps_not_available.log"

    def get_cached_token(self, tokencachefile):
        try:
            with open(tokencachefile, 'r') as tcf:
                token = tcf.readline()
                if len(token) == 0:
                    token = None
        except IOError: # cache file does not exists
            token = None
        return token

    def write_cached_token(self, tokencachefile, token):
        try:
            # creates cachefir if not exists
            cachedir = os.path.dirname(tokencachefile)
            if not os.path.exists(cachedir):
                os.mkdir(cachedir)
            with open(tokencachefile, 'w') as tcf:
                tcf.write(token)
        except IOError as e:
            raise IOError("Failed to write token to cache file: %s %s" % (tokencachefile, e.strerror))


    def retrieve_token(self, token_url, force_new=False):
        token = self.get_cached_token(self.tokencachefile)
        if token is not None and not force_new:
            logging(self, "Using cached token.")
            return token
        logging(self, "Retrieving token ...")
        r = requests.get(token_url)
        token = r.text
        logging(self, "Token: %s" % token)
        if token == 'Auth error':
            print 'Token dispenser auth error, probably too many connections'
            sys.exit(ERRORS.TOKEN_DISPENSER_AUTH_ERROR)
        elif token == "Server error":
            print 'Token dispenser server error'
            sys.exit(ERRORS.TOKEN_DISPENSER_SERVER_ERROR)
        self.token = token
        self.write_cached_token(self.tokencachefile, token)
        return token

    def set_download_folder(self, folder):
        self.config["download_folder_path"] = folder

    def connect_to_googleplay_api(self):
        api = GooglePlayAPI(androidId=self.config["android_id"], lang=self.config["language"])
        error = None
        try:
            if self.token is False:
                logging(self, "Using credentials to connect to API")
                username = self.config["gmail_address"]
                passwd = None
                if self.config["gmail_password"]:
                    logging(self, "Using plaintext password")
                    passwd = self.config["gmail_password"]
                elif self.config["keyring_service"] and HAVE_KEYRING == True:
                    passwd = keyring.get_password(self.config["keyring_service"], username)
                elif self.config["keyring_service"] and HAVE_KEYRING == False:
                    print "You asked for keyring service but keyring package is not installed"
                    sys.exit(ERRORS.KEYRING_NOT_INSTALLED)
                api.login(username, passwd, None)
            else:
                logging(self, "Using token to connect to API")
                api.login(None, None, self.token)
        except LoginError, exc:
            error = exc.value
            success = False
        else:
            self.playstore_api = api
            try:
                self.raw_search(list(), 'firefox', 1)
            except (ValueError, IndexError) as ve: # invalid token or expired
                logging(self, "Token has expired or is invalid. Retrieving a new one...")
                self.retrieve_token(self.token_url, force_new=True)
                api.login(None, None, self.token)
            success = True
        return success, error

    # List apks in the given folder
    def list_folder_apks(self, folder):
        list_of_apks = [filename for filename in os.listdir(folder) if filename.endswith(".apk")]
        return list_of_apks

    def get_bulk_details(self, list_of_apks):
        try:
            results = self.playstore_api.bulkDetails(list_of_apks)
        except DecodeError:
            time.sleep(1)
            results = self.playstore_api.bulkDetails(list_of_apks)
        details = dict()
        for pos, apk in enumerate(list_of_apks):
            det = results.entry[pos]
            doc = det.doc
            details[apk] = [doc.title,
                            doc.creator,
                            self.sizeof_fmt(doc.details.appDetails.installationSize),
                            doc.details.appDetails.numDownloads,
                            doc.details.appDetails.uploadDate,
                            doc.docid,
                            str(doc.details.appDetails.versionCode),
                            "%.2f" % doc.aggregateRating.starRating
                            ]
        return details

    def prepare_analyse_apks(self):
        download_folder_path = self.config["download_folder_path"]
        list_of_apks = [filename for filename in os.listdir(download_folder_path) if
                        os.path.splitext(filename)[1] == ".apk"]
        if len(list_of_apks) > 0:
            logging(self, "Checking apks ...")
            self.analyse_local_apks(list_of_apks, self.playstore_api, download_folder_path,
                                    self.prepare_download_updates)

    def analyse_local_apks(self, list_of_apks, playstore_api, download_folder_path, return_function):
        list_apks_to_update = []
        package_bunch = []
        for position, filename in enumerate(list_of_apks):
            filepath = os.path.join(download_folder_path, filename)
            a = androguard_apk.APK(filepath)
            packagename = a.get_package()
            package_bunch.append(packagename)

        # BulkDetails requires only one HTTP request
        # Get APK info from store
        details = playstore_api.bulkDetails(package_bunch)
        for detail, packagename, filename in zip(details.entry, package_bunch, list_of_apks):
            logging(self, "Analyzing %s" % packagename)
            # Getting Apk infos
            filepath = os.path.join(download_folder_path, filename)
            a = androguard_apk.APK(filepath)
            apk_version_code = a.get_androidversion_code()
            m = detail
            doc = m.doc
            store_version_code = doc.details.appDetails.versionCode

            # Compare
            if apk_version_code != "" and int(apk_version_code) < int(store_version_code) and int(
                    store_version_code) != 0:
                # Add to the download list
                list_apks_to_update.append([packagename, filename, int(apk_version_code), int(store_version_code)])

        return_function(list_apks_to_update)

    def prepare_download_updates(self, list_apks_to_update):
        if len(list_apks_to_update) > 0:
            list_of_packages_to_download = []

            # Ask confirmation before downloading
            message = u"The following applications will be updated :"
            for packagename, filename, apk_version_code, store_version_code in list_apks_to_update:
                message += u"\n%s Version : %s -> %s" % (filename, apk_version_code, store_version_code)
                list_of_packages_to_download.append([packagename, filename])
            message += "\n"
            print message
            if not self.yes:
                print "\nDo you agree?"
                return_value = raw_input('y/n ?')

            if self.yes or return_value == 'y':
                logging(self, "Downloading ...")
                downloaded_packages = self.download_selection(self.playstore_api, list_of_packages_to_download,
                                                              self.after_download)
                return_string = str()
                for package in downloaded_packages:
                    return_string += package + " "
                print "Updated: " + return_string[:-1]
        else:
            print "Everything is up to date !"
            sys.exit(ERRORS.OK)

    def download_selection(self, playstore_api, list_of_packages_to_download, return_function):
        success_downloads = list()
        failed_downloads  = list()
        unavail_downloads = list()

        # BulkDetails requires only one HTTP request
        # Get APK info from store
        details = playstore_api.bulkDetails([item for item, item2 in list_of_packages_to_download])
        position = 1
        for detail, item in zip(details.entry, list_of_packages_to_download):
            packagename, filename = item

            logging(self, "%s / %s %s" % (position, len(list_of_packages_to_download), packagename))

            # Check for download folder
            download_folder_path = self.config["download_folder_path"]
            if not os.path.isdir(download_folder_path):
                os.mkdir(download_folder_path)

            # Get the version code and the offer type from the app details
            # m = playstore_api.details(packagename)
            m = detail
            doc = m.doc
            vc = doc.details.appDetails.versionCode

            # Download
            try:
                if doc.offer[0].checkoutFlowRequired:
                    data = playstore_api.delivery(packagename, vc, progress_bar=self.progress_bar)
                else:
                    data = playstore_api.download(packagename, vc, progress_bar=self.progress_bar)
                success_downloads.append(packagename)
            except IndexError as exc:
                print "Error while downloading %s : %s" % (packagename,
                                                           "this package does not exist, "
                                                           "try to search it via --search before")
                unavail_downloads.append((item, exc))
            except Exception as exc:
                print "Error while downloading %s : %s" % (packagename, exc)
                failed_downloads.append((item, exc))
            else:
                if filename is None:
                    filename = packagename + ".apk"
                filepath = os.path.join(download_folder_path, filename)

                try:
                    open(filepath, "wb").write(data)
                except IOError, exc:
                    print "Error while writing %s : %s" % (packagename, exc)
                    failed_downloads.append((item, exc))
            position += 1

        success_items = set(success_downloads)
        failed_items  = set([item[0] for item, error in failed_downloads])
        unavail_items = set([item[0] for item, error in unavail_downloads])
        to_download_items = set([item[0] for item in list_of_packages_to_download])

        if self.logging:
            self.write_logfiles(success_items, failed_items, unavail_items)

        return_function(failed_downloads + unavail_downloads)
        return to_download_items - failed_items

    def after_download(self, failed_downloads):
        # Info message
        if len(failed_downloads) == 0:
            message = "Download complete"
        else:
            message = "A few packages could not be downloaded :"
            for item, exception in failed_downloads:
                package_name, filename = item
                if filename is not None:
                    message += "\n%s : %s" % (filename, package_name)
                else:
                    message += "\n%s" % package_name
                message += "\n%s\n" % exception

        print message

    def sizeof_fmt(self, num):
        for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0

    def raw_search(self, results_list, search_string, nb_results):
        # Query results
        return self.playstore_api.search(search_string, nb_results=nb_results).doc

    def search(self, results_list, search_string, nb_results, free_only=True, include_headers=True):
        results = self.raw_search(results_list, search_string, nb_results)
        if len(results) < 1:
            print "No result"
            return
        all_results = list()
        if include_headers:
            # Name of the columns
            col_names = ["Title", "Creator", "Size", "Downloads", "Last Update", "AppID", "Version", "Rating"]
            all_results.append(col_names)
        # Compute results values
        for docs in results:
            for result in docs.child:
                if free_only and result.offer[0].checkoutFlowRequired:  # if not Free to download
                    continue
                l = [result.title,
                     result.creator,
                     self.sizeof_fmt(result.details.appDetails.installationSize),
                     result.details.appDetails.numDownloads,
                     result.details.appDetails.uploadDate,
                     result.docid,
                     result.details.appDetails.versionCode,
                     "%.2f" % result.aggregateRating.starRating
                     ]
                if len(all_results) < int(nb_results)+1:
                    all_results.append(l)

        if self.verbose:
            # Print a nice table
            col_width = list()
            for column_indice in range(len(all_results[0])):
                col_length = max([len(u"%s" % row[column_indice]) for row in all_results])
                col_width.append(col_length + 2)

            for result in all_results:
                print "".join((u"%s" % item).encode('utf-8').strip().ljust(col_width[indice]) for indice, item in
                              enumerate(result))
        return all_results

    def download_packages(self, list_of_packages_to_download):
        self.download_selection(self.playstore_api, [(pkg, None) for pkg in list_of_packages_to_download],
                                self.after_download)

    def write_logfiles(self, success, failed, unavail):
        if len(success) != 0:
            with open(self.success_logfile, 'w') as logfile:
                for package in success:
                    logfile.write('%s\n' % package)

        if len(failed) != 0:
            with open(self.failed_logfile, 'w') as logfile:
                for package in failed:
                    logfile.write('%s\n' % package)

        if len(unavail) != 0:
            with open(self.unavail_logfile, 'w') as logfile:
                for package in unavail:
                    logfile.write('%s\n' % package)


def install_cronjob(automatic=False):
    import shutil
    import stat
    cred_default = '/etc/gplaycli/gplaycli.conf'
    fold_default = '/opt/apks'
    frequence_default = "/etc/cron.daily"

    if not automatic:
        credentials = raw_input('path to gplaycli.conf? let empty for ' + cred_default + '\n') or cred_default
        folder_to_update = raw_input('path to apks folder? let empty for ' + fold_default + '\n') or fold_default
        frequence = raw_input('update it [d]aily or [w]eekly?\n')
        if frequence == 'd':
            frequence_folder = '/etc/cron.daily'
        elif frequence == 'w':
            frequence_folder = '/etc/cron.weekly'
        else:
            raise Exception('please type d/w to make your choice')

    else:
        credentials = cred_default
        folder_to_update = fold_default
        frequence_folder = frequence_default

    frequence_file = frequence_folder + '/gplaycli'
    shutil.copyfile('/etc/gplaycli/cronjob', frequence_file)

    with open('/etc/gplaycli/cronjob', 'r') as fi:
        with open(frequence_file, 'w') as fo:
            for line in fi:
                line = line.replace('PL_FOLD', folder_to_update)
                line = line.replace('PL_CRED', credentials)
                fo.write(line)

    st = os.stat(frequence_file)
    os.chmod(frequence_file, st.st_mode | stat.S_IEXEC)
    print('Cronjob installed at ' + frequence_file)
    return ERRORS.OK


def logging(gpc, message):
    if gpc.verbose:
        print message

def load_from_file(filename):
    return [ package.strip('\r\n') for package in open(filename).readlines() ]

def main():
    parser = argparse.ArgumentParser(description="A Google Play Store Apk downloader and manager for command line")
    parser.add_argument('-V', '--version', action='store_true', dest='version', help='Print version number and exit')
    parser.add_argument('-y', '--yes', action='store_true', dest='yes_to_all', help='Say yes to all prompted questions')
    parser.add_argument('-l', '--list', action='store', dest='list', metavar="FOLDER",
                        type=str, help="List APKS in the given folder, with details")
    parser.add_argument('-s', '--search', action='store', dest='search_string', metavar="SEARCH",
                        type=str, help="Search the given string in Google Play Store")
    parser.add_argument('-P', '--paid', action='store_true', dest='paid', default=False, help='Also search for paid apps')
    parser.add_argument('-n', '--number', action='store', dest='number_results', metavar="NUMBER",
                        type=str, help="For the search option, returns the given number of matching applications")
    parser.add_argument('-d', '--download', action='store', dest='packages_to_download', metavar="AppID", nargs="+",
                        type=str, help="Download the Apps that map given AppIDs")
    parser.add_argument('-F', '--file', action='store', dest='load_from_file', metavar="FILE",
                        type=str, help="Load packages to download from file, one package per line")
    parser.add_argument('-u', '--update', action='store', dest='update_folder', metavar="FOLDER",
                        type=str, help="Update all APKs in a given folder")
    parser.add_argument('-f', '--folder', action='store', dest='dest_folder', metavar="FOLDER", nargs=1,
                        type=str, default=".", help="Where to put the downloaded Apks, only for -d command")
    parser.add_argument('-t', '--token', action='store_true', dest='token', default=False, help='Instead of classical credentials, use the tokenize version')
    parser.add_argument('-tu', '--token-url', action='store', dest='token_url', metavar="TOKEN_URL",
                        type=str, default="DEFAULT_URL", help="Use the given tokendispenser URL to retrieve a token")
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help='Be verbose')
    parser.add_argument('-c', '--config', action='store', dest='config', metavar="CONF_FILE", nargs=1,
                        type=str, default=None, help="Use a different config file than gplaycli.conf")
    parser.add_argument('-p', '--progress', action='store_true', dest='progress_bar',
                        help='Prompt a progress bar while downloading packages')
    parser.add_argument('-L', '--log', action='store_true', dest='enable_logging', default=False,
                        help='Enable logging of apps status. Downloaded, failed, not available apps will be written in separate logging files')
    parser.add_argument('-ic', '--install-cronjob', action='store_true', dest='install_cronjob',
                        help='Install cronjob for regular APKs update. Use --yes to automatically install to default locations')

    if len(sys.argv) < 2:
        sys.argv.append("-h")

    args = parser.parse_args()

    if args.version:
        print __version__
        return

    if args.install_cronjob:
        sys.exit(install_cronjob(args.yes_to_all))

    cli = GPlaycli(args, args.config)
    success = False
    while (not success) and (cli.retries != 0):
        success, error = cli.connect_to_googleplay_api()
        if not success:
            cli.retries -= 1
            logging(cli, "Cannot login to GooglePlay ( %s ), remaining tries %s" % (error, cli.retries))
        if cli.retries == 0:
            sys.exit(ERRORS.CANNOT_LOGIN_GPLAY)

    if args.list:
        print cli.list_folder_apks(args.list)

    if args.update_folder:
        cli.prepare_analyse_apks()

    if args.search_string:
        cli.verbose = True
        nb_results = 10
        if args.number_results:
            nb_results = args.number_results
        cli.search(list(), args.search_string, nb_results, not args.paid)

    if args.load_from_file:
        args.packages_to_download = load_from_file(args.load_from_file)

    if args.packages_to_download is not None:
        if args.dest_folder is not None:
            cli.set_download_folder(args.dest_folder[0])
        cli.download_packages(args.packages_to_download)


if __name__ == '__main__':
    main()
