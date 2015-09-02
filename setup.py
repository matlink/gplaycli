from setuptools import setup, Command
import os

setup(name='GPlayCli',
        version='0.1.2',
        description='GPlayCli, a Google play downloader command line interface',
        author="Matlink",
        author_email="matlink@matlink.fr",
        url="https://github.com/matlink/gplaycli",
        license="AGPLv3",
        scripts=['gplaycli/gplaycli'],
        packages=[
            'ext_libs/androguard/core/bytecodes/libdvm/',    
            'ext_libs/androguard/core/bytecodes/',    
            'ext_libs/androguard/core/',    
            'ext_libs/androguard/',    
            'ext_libs/googleplay_api/',    
            'ext_libs/',    
            'gplaycli/',
        ], 
        data_files=[
            ['/etc/gplaycli/', ['credentials.conf','cron/cronjob']],
        ],
        install_requires=[
                'requests',
                'protobuf',
                'ndg-httpsclient',
                'clint',
		'pyasn1',
        ],
    )
