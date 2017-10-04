from setuptools import setup

setup(
    name='googleplay-api',
    version='0.1.2',
    description='Unofficial python3 api for google play',
    url='https://github.com/NoMore201/googleplay-api',
    author='NoMore201',
    author_email='domenico.iezzi.201@gmail.com',
    license='MIT',
    packages=['gpapi'],
    package_data={
        'gpapi': ['device.properties'],
    },
    install_requires=['pycrypto',
                     'protobuf',
                     'requests'],
)
