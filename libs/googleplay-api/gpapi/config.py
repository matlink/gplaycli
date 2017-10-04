from . import googleplay_pb2
import time
import os
import sys

VERSION = sys.version_info[0]
if VERSION == 2:
    import ConfigParser
else:
    import configparser

# separator used by search.py, categories.py, ...
SEPARATOR = ";"

LANG            = "en_US"
GOOGLE_PUBKEY   = "AAAAgMom/1a/v0lblO2Ubrt60J2gcuXSljGFQXgcyZWveWLEwo6prwgi3iJIZdodyhKZQrNWp5nKJ3srRXcUW+F1BD3baEVGcmEgqaLZUNBjm057pKRI16kB0YppeGx5qIQ5QjKzsR8ETQbKLNWgRY0QRNVz34kMJR3P/LgHax/6rmf5AAAAAwEAAQ=="

# parse phone config from the file 'device.properties'.
# if you want to add another phone, just create another section in
# the file. Some configurations for common phones can be found here:
# https://github.com/yeriomin/play-store-api/tree/master/src/main/resources
if VERSION == 2:
    config = ConfigParser.ConfigParser()
else:
    config = configparser.ConfigParser()

filepath = os.path.join( os.path.dirname( os.path.realpath(__file__) ), 'device.properties')
config.read(filepath)
device = {}
for (key, value) in config.items('angler'):
    device[key] = value

def getDeviceConfig():
    libList = device['sharedlibraries'].split(",")
    featureList = device['features'].split(",")
    localeList = device['locales'].split(",")
    glList = device['gl.extensions'].split(",")
    platforms = device['platforms'].split(",")

    deviceConfig = googleplay_pb2.DeviceConfigurationProto()
    deviceConfig.touchScreen = int(device['touchscreen'])
    deviceConfig.keyboard = int(device['keyboard'])
    deviceConfig.navigation = int(device['navigation'])
    deviceConfig.screenLayout = int(device['screenlayout'])
    deviceConfig.hasHardKeyboard = False if device['hashardkeyboard'] == 'false' else True
    deviceConfig.hasFiveWayNavigation = False if device['hasfivewaynavigation'] == 'false' else True
    deviceConfig.screenDensity = int(device['screen.density'])
    deviceConfig.screenWidth = int(device['screen.width'])
    deviceConfig.screenHeight = int(device['screen.height'])
    deviceConfig.glEsVersion = int(device['gl.version'])
    for x in platforms:
        deviceConfig.nativePlatform.append(x)
    for x in libList:
        deviceConfig.systemSharedLibrary.append(x)
    for x in featureList:
        deviceConfig.systemAvailableFeature.append(x)
    for x in localeList:
        deviceConfig.systemSupportedLocale.append(x)
    for x in glList:
        deviceConfig.glExtension.append(x)
    return deviceConfig

def getAndroidBuild():
    androidBuild = googleplay_pb2.AndroidBuildProto()
    androidBuild.id = device['build.fingerprint']
    androidBuild.product = device['build.hardware']
    androidBuild.carrier = device['build.brand']
    androidBuild.radio = device['build.radio']
    androidBuild.bootloader = device['build.bootloader']
    androidBuild.device = device['build.device']
    androidBuild.sdkVersion = int(device['build.version.sdk_int'])
    androidBuild.model = device['build.model']
    androidBuild.manufacturer = device['build.manufacturer']
    androidBuild.buildProduct = device['build.product']
    androidBuild.client = device['client']
    androidBuild.otaInstalled = False
    androidBuild.timestamp = int(time.time())
    androidBuild.googleServices = int(device['gsf.version'])
    return androidBuild

def getAndroidCheckin():
    androidCheckin = googleplay_pb2.AndroidCheckinProto()
    androidCheckin.build.CopyFrom(getAndroidBuild())
    androidCheckin.lastCheckinMsec = 0
    androidCheckin.cellOperator = device['celloperator']
    androidCheckin.simOperator = device['simoperator']
    androidCheckin.roaming = device['roaming']
    androidCheckin.userNumber = 0
    return androidCheckin

def getAndroidCheckinRequest():
    request = googleplay_pb2.AndroidCheckinRequest()
    request.id = 0
    request.checkin.CopyFrom(getAndroidCheckin())
    request.locale = 'en_US'
    request.timeZone = 'America/New_York'
    request.version = 3
    request.deviceConfiguration.CopyFrom(getDeviceConfig())
    request.fragment = 0
    return request
