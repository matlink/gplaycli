from setuptools import setup
import os
import sys

with open("README.md", "r") as fh:
	long_description = fh.read()

setup(name='gplaycli',
		version='3.29',
		description='GPlayCli, a Google play downloader command line interface',
		long_description=long_description,
		long_description_content_type="text/markdown",
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
				'matlink-gpapi>=0.4.4.4',
				'pyaxmlparser',
		],
)
