# gplaycli [![Build Status](https://travis-ci.org/matlink/gplaycli.svg?branch=master)](https://travis-ci.org/matlink/gplaycli)
Google Play Downloader via Command line, based on https://framagit.org/tuxicoman/googleplaydownloader See package Readme for python modules to install.

GPlayCli is a command line tool to search, install, update Android applications from the Google Play Store. The main goal was to be able to run this script with a cronjob, in order to automatically update an F-Droid server instance.


	$ gplaycli --help
	usage: gplaycli [-h] [-V] [-y] [-l FOLDER] [-s SEARCH] [-P] [-n NUMBER]
	                [-d AppID [AppID ...]] [-F FILE] [-u FOLDER] [-f FOLDER]
	                [-dc DEVICE_CODENAME] [-t] [-tu TOKEN_URL] [-v] [-c CONF_FILE]
	                [-p] [-L] [-ic]

	A Google Play Store Apk downloader and manager for command line

	optional arguments:
	  -h, --help            show this help message and exit
	  -V, --version         Print version number and exit
	  -y, --yes             Say yes to all prompted questions
	  -l FOLDER, --list FOLDER
	                        List APKS in the given folder, with details
	  -s SEARCH, --search SEARCH
	                        Search the given string in Google Play Store
	  -P, --paid            Also search for paid apps
	  -n NUMBER, --number NUMBER
	                        For the search option, returns the given number of
	                        matching applications
	  -d AppID [AppID ...], --download AppID [AppID ...]
	                        Download the Apps that map given AppIDs
	  -F FILE, --file FILE  Load packages to download from file, one package per
	                        line
	  -u FOLDER, --update FOLDER
	                        Update all APKs in a given folder
	  -f FOLDER, --folder FOLDER
	                        Where to put the downloaded Apks, only for -d command
	  -dc DEVICE_CODENAME, --device-codename DEVICE_CODENAME
	                        The device codename to fake
	  -t, --token           Instead of classical credentials, use the tokenize
	                        version
	  -tu TOKEN_URL, --token-url TOKEN_URL
	                        Use the given tokendispenser URL to retrieve a token
	  -v, --verbose         Be verbose
	  -c CONF_FILE, --config CONF_FILE
	                        Use a different config file than gplaycli.conf
	  -p, --progress        Prompt a progress bar while downloading packages
	  -L, --log             Enable logging of apps status. Downloaded, failed, not
	                        available apps will be written in separate logging
	                        files
	  -ic, --install-cronjob
	                        Install cronjob for regular APKs update. Use --yes to
	                        automatically install to default locations

Changelog
=========
See https://github.com/matlink/gplaycli/releases for releases and changelogs

Installation
============

- Best way to install it is using pip3: `pip3 install gplaycli` or `pip3 install gplaycli --user` if you are non-root
- Cleanest way is using virtualenv: `virtualenv gplaycli; cd gplaycli; source bin/activate`, then either `pip install gplaycli` or `git clone https://github.com/matlink/gplaycli && pip3 install ./gplaycli/`. Make sure `virtualenv` is initialized with Python 3. If it's not, use `virtualenv -p python3`.

Debian installation
--------------------
Releases are available here https://github.com/matlink/gplaycli/releases/ as debian packages. If you prefer not to use debian packaging, check the following method.

Requirements
----------
Works on GNU/Linux or Windows with `pip` and Python 3. First of all, ensure these packages are installed on your system : 

- python3-dev package -> `apt-get install python3-dev`
- libffi package -> `apt-get install libffi-dev`
- libssl-dev -> `apt-get install libssl-dev` (for pypi's `cryptography` compilation)
- python (>=3)

Then, you need to install it with some needed libraries using either `pip3 install gplaycli` or `python3 setup.py install` after cloning it, then it will be available with `gplaycli` command. If you don't want to install it, only install requirements with `pip install -r requirements.txt` and use it as it.

If you want to use your own Google credentials, simply change them in the `credentials.conf` file with your own settings. 

~~If you want to generate androidID, see https://github.com/nviennot/android-checkin/ or https://github.com/Akdeniz/google-play-crawler, otherwise you could either use the given one (default) or use one of your devices ID.~~

Currently looking for a solution (`googleplaydownloader` from Tuxicoman provides a working `jar`).

If you plan to use it with F-Droid-server, remember that fdroidserver needs Java (more precisely the 'jar' command) to work.

Uninstall
=========
Use `pip uninstall gplaycli`, and remove conf and cronjob with `rm -rf /etc/gplaycli /etc/cron.daily/gplaycli`. Should be clean, except python dependencies for gplaycli.
