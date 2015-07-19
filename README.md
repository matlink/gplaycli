# gplay-cli
Google Play Downloader via Command line, based on https://codingteam.net/project/googleplaydownloader See package Readme for python modules to install.

GPlayCli is a command line tool to search, install, update Android applications from the Google Play Store. The main goal was to be able to run this script with a cronjob, in order to automatically update an F-Droid server instance.

	$ ./gplay-cli.py 
	usage: gplay-cli.py [-h] [-y] [-s SEARCH] [-n NUMBER] [-d AppID [AppID ...]]
                    [-u FOLDER] [-f FOLDER] [-v] [-c CONF_FILE] [-p]

		A Google Play Store Apk downloader and manager for command line

		optional arguments:
		  -h, --help            show this help message and exit
		  -y, --yes             Say yes to all prompted questions
		  -s SEARCH, --search SEARCH
		                        Search the given string in Google Play Store
		  -n NUMBER, --number NUMBER
		                        For the search option, returns the given number of
		                        matching applications
		  -d AppID [AppID ...], --download AppID [AppID ...]
		                        Download the Apps that map given AppIDs
		  -u FOLDER, --update FOLDER
		                        Update all APKs in a given folder
		  -f FOLDER, --folder FOLDER
		                        Where to put the downloaded Apks, only for -d command
		  -v, --verbose         Be verbose
		  -c CONF_FILE, --config CONF_FILE
		                        Use a different config file than credentials.conf
		  -p, --progress        Prompt a progress bar while downloading packages

Requirements
----------
Works on GNU/Linux or Windows with `pip` and Python 2.9+. First of all, ensure these packages are installed on your system : 

- python-dev package -> `apt-get install python-dev`
- libffi package -> `apt-get install libffi-dev`
- python (>=2.5)

Then, you need to install some needed libraries with `pip` (consider using a venv):

- python-protobuf (>=2.4) to talk to Google Play Store -> `pip install protobuf`
- python-requests (>=0.12) -> `pip install requests`
- python-ndg-httpsclient for SSL connexions -> `pip install ndg-httpsclient`
- python-clint for progress bar -> `pip install clint`

If you want to use your own Google credentials, simply change them in the `credentials.conf` file with your own settings. 
If you want to generate androidID, see https://github.com/nviennot/android-checkin/, otherwise you could either use the given one (default) or use one of your devices ID.
