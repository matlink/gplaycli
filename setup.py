from setuptools import setup, Command
import os

setup(name='GPlayCli',
        version='0.2.1',
        description='GPlayCli, a Google play downloader command line interface',
        author="Matlink",
        author_email="matlink@matlink.fr",
        url="https://github.com/matlink/gplaycli",
        license="AGPLv3",
        scripts=['gplaycli/gplaycli'],
        packages=[
            'ext_libs/googleplay_api/',    
            'ext_libs/',    
            'gplaycli/',
        ], 
        data_files=[
            [os.path.expanduser('~')+'/.config/gplaycli/', ['credentials.conf','cron/cronjob']],
        ],
        install_requires=[
                'requests >= 2.0.0',
                'protobuf',
                'ndg-httpsclient',
                'androguard',
                'clint',
		'pyasn1',
        ],
    )
