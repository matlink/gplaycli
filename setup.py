from setuptools import setup
import os
import sys

setup(name='gplaycli',
		version='3.28',
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
			['etc/gplaycli', ['gplaycli.conf']],
		],
		install_requires=[
				'gpapi>=0.4.4',
				'pyaxmlparser',
		],
)
