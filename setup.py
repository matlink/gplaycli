from setuptools import setup, Command
import os
import sys

if sys.version_info[0] == 2:
    basedir = 'python2'
    python3 = False
else:
    basedir = 'python3'
    python3 = True


setup(name='GPlayCli',
        version='2.15',
        description='GPlayCli, a Google play downloader command line interface',
        author="Matlink",
        author_email="matlink@matlink.fr",
        url="https://github.com/matlink/gplaycli",
        license="AGPLv3",
        scripts=[basedir+'/gplaycli/gplaycli'],
        packages=[
            'ext_libs.googleplay_api',
            'ext_libs',
            'gplaycli',
        ],
        package_dir={
            'ext_libs.googleplay_api': basedir+'/ext_libs/googleplay_api',
            'ext_libs': basedir+'/ext_libs',
            'gplaycli': basedir+'/gplaycli',
        },
        data_files=[
            [os.path.expanduser('~')+'/.config/gplaycli/', ['gplaycli.conf','cron/cronjob']],
        ],
        install_requires=[
                'requests >= 2.0.0',
                'protobuf',
                'ndg-httpsclient',
                'clint',
		'pyasn1',
                'pycrypto',
                'pyaxmlparser' if python3 else 'androguard',
        ],
)
