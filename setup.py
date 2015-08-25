from setuptools import setup, Command
import os

setup(name='GPlayCli',
        version='0.1',
        description='GPlayCli, a Google play downloader command line interface',
        author="Matlink",
        author_email="matlink@matlink.fr",
        url="https://github.com/matlink/gplaycli",
        license="AGPLv3",
        scripts=['gplaycli'],
        packages=[
            'ext_libs/androguard/core/bytecodes/libdvm/',    
            'ext_libs/androguard/core/bytecodes/',    
            'ext_libs/androguard/core/',    
            'ext_libs/androguard/',    
            'ext_libs/googleplay_api/',    
            'ext_libs/',    
        ], 
        data_files=[
            ['/etc/gplaycli/', ['credentials.conf']],
        ],
        install_requires=[
                'requests',
                'protobuf',
                'ndg-httpsclient',
                'clint',
		'pyasn1',
        ],
    )
