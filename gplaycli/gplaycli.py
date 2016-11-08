#! /usr/bin/python2
# -*- coding: utf-8 -*-
"""
GPlay-Cli
Copyleft (C) 2015 Matlink
Hardly based on GooglePlayDownloader https://codingteam.net/project/googleplaydownloader
Copyright (C) 2013   Tuxicoman

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
from ext_libs.googleplay_api.googleplay import GooglePlayAPI  # GooglePlayAPI
from ext_libs.googleplay_api.googleplay import LoginError
from androguard.core.bytecodes import apk as androguard_apk  # Androguard
from google.protobuf.message import DecodeError


class GPlaycli(object):
    def __init__(self, credentials="credentials.conf"):
        # If credentials are not specified on command line, get default conffile
        if credentials == 'credentials.conf' and not os.path.isfile(credentials):
            credentials = '/etc/gplaycli/credentials.conf'
        # Overide credentials if present in .config
        config_file = os.path.expanduser("~")+'/.config/gplaycli/credentials.conf'
        if os.path.isfile(config_file):
            credentials = config_file
        self.configparser = ConfigParser.ConfigParser()
        self.configparser.read(credentials)
        self.config = dict()
        for key, value in self.configparser.items("Credentials"):
            self.config[key] = value
        self.yes = False
        self.verbose = False
        self.progress_bar = False

    def set_download_folder(self, folder):
        self.config["download_folder_path"] = folder

    def connect_to_googleplay_api(self):
        api = GooglePlayAPI(androidId=self.config["android_id"], lang=self.config["language"])
        error = None
        try:
            api.login(self.config["gmail_address"], self.config["gmail_password"], None)
        except LoginError, exc:
            error = exc.value
            success = False
        else:
            self.playstore_api = api
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
            if self.verbose:
                print "Checking apks ..."
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
            if self.verbose:
                print "Analyzing %s" % packagename
            # Getting Apk infos
            filepath = os.path.join(download_folder_path, filename)
            a = androguard_apk.APK(filepath)
            apk_version_code = a.get_androidversion_code()
            m = detail
            doc = m.doc
            store_version_code = doc.details.appDetails.versionCode

            # Compare
            if apk_version_code != "" and int(apk_version_code) != int(store_version_code) and int(
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
            message += "\n\nDo you agree?"
            print message
            if not self.yes:
                return_value = raw_input('y/n ?')

            if self.yes or return_value == 'y':
                if self.verbose:
                    print "Downloading ..."
                downloaded_packages = self.download_selection(self.playstore_api, list_of_packages_to_download,
                                                              self.after_download)
                return_string = str()
                for package in downloaded_packages:
                    return_string += package + " "
                print "Updated: " + return_string[:-1]
        else:
            print "Everything is up to date !"
            sys.exit(0)

    def download_selection(self, playstore_api, list_of_packages_to_download, return_function):
        failed_downloads = []

        # BulkDetails requires only one HTTP request
        # Get APK info from store
        details = playstore_api.bulkDetails([item for item, item2 in list_of_packages_to_download])
        position = 1
        for detail, item in zip(details.entry, list_of_packages_to_download):
            packagename, filename = item
            if self.verbose:
                print str(position) + "/" + str(len(list_of_packages_to_download)), packagename

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
                data = playstore_api.download(packagename, vc, progress_bar=self.progress_bar)
            except IndexError as exc:
                print "Error while downloading %s : %s" % (packagename,
                                                           "this package does not exist, "
                                                           "try to search it via --search before")
                failed_downloads.append((item, exc))
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

        failed_items = set([item[0] for item, error in failed_downloads])
        to_download_items = set([item[0] for item in list_of_packages_to_download])
        return_function(failed_downloads)
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
        if len(results) > 0:
            results = results[0].child
        else:
            print "No result"
            return
        all_results = list()
        if include_headers:
            # Name of the columns
            col_names = ["Title", "Creator", "Size", "Downloads", "Last Update", "AppID", "Version", "Rating"]
            all_results.append(col_names)
        # Compute results values
        for result in results:
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


def install_cronjob():
    import shutil
    import stat
    cred_default = '/etc/gplaycli/credentials.conf'
    credentials = raw_input('path to credentials.conf? let empty for ' + cred_default + '\n') or cred_default
    fold_default = '/opt/apks'
    folder_to_update = raw_input('path to apks folder? let empty for ' + fold_default + '\n') or fold_default
    frequence = raw_input('update it [d]aily or [w]eekly?\n')
    if frequence == 'd':
        frequence_folder = '/etc/cron.daily'
    elif frequence == 'w':
        frequence_folder = '/etc/cron.weekly'
    else:
        raise Exception('please type d/w to make your choice')

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
    return 0


def main():
    parser = argparse.ArgumentParser(description="A Google Play Store Apk downloader and manager for command line")
    parser.add_argument('-y', '--yes', action='store_true', dest='yes_to_all', help='Say yes to all prompted questions')
    parser.add_argument('-l', '--list', action='store', dest='list', metavar="FOLDER",
                        type=str, help="List APKS in the given folder, with details")
    parser.add_argument('-s', '--search', action='store', dest='search_string', metavar="SEARCH",
                        type=str, help="Search the given string in Google Play Store")
    parser.add_argument('-n', '--number', action='store', dest='number_results', metavar="NUMBER",
                        type=str, help="For the search option, returns the given number of matching applications")
    parser.add_argument('-d', '--download', action='store', dest='packages_to_download', metavar="AppID", nargs="+",
                        type=str, help="Download the Apps that map given AppIDs")
    parser.add_argument('-u', '--update', action='store', dest='update_folder', metavar="FOLDER",
                        type=str, help="Update all APKs in a given folder")
    parser.add_argument('-f', '--folder', action='store', dest='dest_folder', metavar="FOLDER", nargs=1,
                        type=str, default=".", help="Where to put the downloaded Apks, only for -d command")
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help='Be verbose')
    parser.add_argument('-c', '--config', action='store', dest='config', metavar="CONF_FILE", nargs=1,
                        type=str, default="credentials.conf", help="Use a different config file than credentials.conf")
    parser.add_argument('-p', '--progress', action='store_true', dest='progress_bar',
                        help='Prompt a progress bar while downloading packages')
    parser.add_argument('-ic', '--install-cronjob', action='store_true', dest='install_cronjob',
                        help='Interactively install cronjob for regular APKs update')

    if len(sys.argv) < 2:
        sys.argv.append("-h")

    args = parser.parse_args()

    if args.install_cronjob:
        sys.exit(install_cronjob())

    cli = GPlaycli(args.config)
    cli.yes = args.yes_to_all
    cli.verbose = args.verbose
    cli.progress_bar = args.progress_bar
    cli.set_download_folder(args.update_folder)
    success, error = cli.connect_to_googleplay_api()

    if not success:
        print "Cannot login to GooglePlay (", error, ")"
        sys.exit(1)

    if args.list:
        print cli.list_folder_apks(args.list)

    if args.update_folder:
        cli.prepare_analyse_apks()

    if args.search_string:
        cli.verbose = True
        nb_results = 10
        if args.number_results:
            nb_results = args.number_results
        cli.search(list(), args.search_string, nb_results)

    if args.packages_to_download is not None:
        if args.dest_folder is not None:
            cli.set_download_folder(args.dest_folder[0])
        cli.download_packages(args.packages_to_download)


if __name__ == '__main__':
    main()
