from setuptools import setup
import os
import sys

if sys.version_info[0] == 2:
    basedir = 'python2'
    python2 = True
    python3 = False
else:
    basedir = 'python3'
    python2 = False
    python3 = True


setup(name='GPlayCli',
        version='3.2',
        description='GPlayCli, a Google play downloader command line interface',
        author="Matlink",
        author_email="matlink@matlink.fr",
        url="https://github.com/matlink/gplaycli",
        license="AGPLv3",
        scripts=['gplaycli/gplaycli'],
        packages=[
            'gplaycli',
        ],
        package_dir={
            'gplaycli': 'gplaycli',
        },
        data_files=[
            [os.path.expanduser('~')+'/.config/gplaycli/', ['gplaycli.conf','cron/cronjob']],
        ],
        install_requires=[
                'protobuf',
                'gpapi >= 0.1.5',
                'pyaxmlparser' if python3 else 'androguard',
                'enum34' if python2 else '',
        ],
)
