# gplaycli [![Python package](https://github.com/matlink/gplaycli/workflows/Python%20package/badge.svg)](https://github.com/matlink/gplaycli/actions)
GPlayCli is a command line tool to search, install, update Android applications from the Google Play Store.

	$ usage: gplaycli [-h] [-V] [-v] [-s SEARCH] [-d AppID [AppID ...]] [-y] [-l FOLDER] [-P] [-av] [-a] [-F FILE]
                [-u FOLDER] [-f FOLDER] [-dc DEVICE_CODENAME] [-t] [-tu TOKEN_URL] [-ts TOKEN_STR] [-g GSF_ID]
                [-c CONF_FILE] [-p] [-L]

	A Google Play Store Apk downloader and manager for command line

	optional arguments:
	  -h, --help            show this help message and exit
	  -V, --version         Print version number and exit
	  -v, --verbose         Be verbose
	  -s SEARCH, --search SEARCH
	                        Search the given string in Google Play Store
	  -d AppID [AppID ...], --download AppID [AppID ...]
	                        Download the Apps that map given AppIDs
	  -y, --yes             Say yes to all prompted questions
	  -l FOLDER, --list FOLDER
	                        List APKS in the given folder, with details
	  -P, --paid            Also search for paid apps
	  -av, --append-version
	                        Append versionstring to APKs when downloading
	  -a, --additional-files
	                        Enable the download of additional files
	  -F FILE, --file FILE  Load packages to download from file, one package per line
	  -u FOLDER, --update FOLDER
	                        Update all APKs in a given folder
	  -f FOLDER, --folder FOLDER
	                        Where to put the downloaded Apks, only for -d command
	  -dc DEVICE_CODENAME, --device-codename DEVICE_CODENAME
	                        The device codename to fake
	  -t, --token           Instead of classical credentials, use the tokenize version
	  -tu TOKEN_URL, --token-url TOKEN_URL
	                        Use the given tokendispenser URL to retrieve a token
	  -ts TOKEN_STR, --token-str TOKEN_STR
	                        Supply token string by yourself, need to supply GSF_ID at the same time
	  -g GSF_ID, --gsfid GSF_ID
	                        Supply GSF_ID by yourself, need to supply token string at the same time
	  -c CONF_FILE, --config CONF_FILE
	                        Use a different config file than gplaycli.conf
	  -p, --progress        Prompt a progress bar while downloading packages
	  -L, --log             Enable logging of apps status in separate logging files

Credentials
===========
## Warning
Token authentication is currently out of order since the default token dispenser instance has probably been blacklisted from Google servers.

By default, gplaycli fetches a token from a token dispenser server located at https://matlink.fr/token/email/gsfid to login in Google Play. If you want to use another token dispenser server, change its URL in the configuration file (depends on the way you installed it). If you want to use your own Google credentials, put
	
	token=False

in the config file and type in your credentials in
	
	gmail_address=
	gmail_password=

variables.

Changelog
=========
See https://github.com/matlink/gplaycli/releases for releases and changelogs

Installation
============

Pip
---
- Best way to install it is using pip3: `pip3 install gplaycli` or `pip3 install gplaycli --user` if you are non-root
- Cleanest way is using virtualenv: `virtualenv gplaycli; cd gplaycli; source bin/activate`, then either `pip3 install gplaycli` or `git clone https://github.com/matlink/gplaycli && pip3 install ./gplaycli/`. Make sure `virtualenv` is initialized with Python 3. If it's not, use `virtualenv -p python3`.

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

Then, you need to install it with some needed libraries using either `pip3 install gplaycli` or `python3 setup.py install` after cloning it, then it will be available with `gplaycli` command. If you don't want to install it, only install requirements with `pip3 install -r requirements.txt` and use it as it.

If you want to use your own Google credentials, simply change them in the `gplaycli.conf` file with your own settings. 

If you plan to use it with F-Droid-server, remember that fdroidserver needs Java (more precisely the 'jar' command) to work.

Uninstall
=========
Use `pip uninstall gplaycli`, and remove conf with `rm -rf /etc/gplaycli`. Should be clean, except python dependencies for gplaycli.
