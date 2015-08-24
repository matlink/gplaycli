from setuptools import setup, find_packages
import shutil, os

if not os.path.exists('bin'):
    os.makedirs('bin')
shutil.copyfile('gplaycli.py', 'bin/gplaycli')

setup(name='GPlayCli',
        version='0.1',
        description='GPlayCli, a Google play downloader command line interface',
        author="Matlink",
        author_email="matlink@matlink.fr",
        url="https://github.com/matlink/gplaycli",
        license="AGPLv3",
        scripts=['bin/gplaycli'],
        packages=[
                'ext_libs/androguard',
                'ext_libs/androguard/core',
                'ext_libs/androguard/core/bytecodes',
                'ext_libs/androguard/core/bytecodes/libdvm',
                'ext_libs/googleplay_api'
        ],
        install_requires=[
                'requests',
                'protobuf',
                'ndg-httpsclient',
                'clint',
        ],
    )