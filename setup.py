from setuptools import setup
import os
import sys

if sys.version_info[0] == 2:
    sys.stderr.write("""
    Python2 support has been removed since version 3.9
    Please install GPlayCli with Python3
    Or install version 3.8 but don't expect support""")
    sys.exit(1)

setup(name='GPlayCli',
        version='3.11',
        description='GPlayCli, a Google play downloader command line interface',
        author="Matlink",
        author_email="matlink@matlink.fr",
        url="https://github.com/matlink/gplaycli",
        license="AGPLv3",
        entry_points={
            'console_scripts': [
                'gplaycli = gplaycli.gplaycli:main',
            ],
        },
        packages=[
            'gplaycli',
        ],
        package_dir={
            'gplaycli': 'gplaycli',
        },
        data_files=[
            [os.path.expanduser('~')+'/.config/gplaycli', ['gplaycli.conf','cron/cronjob']],
        ],
        install_requires=[
                'protobuf',
                'gpapi >= 0.1.5',
                'pyaxmlparser',
        ],
)
