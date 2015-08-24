from setuptools import setup, find_packages
import os

setup(name='GPlayCli',
        version='0.1',
        description='GPlayCli, a Google play downloader command line interface',
        author="Matlink",
        author_email="matlink@matlink.fr",
        url="https://github.com/matlink/gplaycli",
        license="AGPLv3",
        scripts=['gplaycli'],
        packages=find_packages(), 
        install_requires=[
                'requests',
                'protobuf',
                'ndg-httpsclient',
                'clint',
        ],
    )
