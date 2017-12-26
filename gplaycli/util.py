import os
import math

def sizeof_fmt(num):
    log = int(math.log(num, 1024))
    return "%.2f%s" % (num/(1024**log), ['bytes','KB','MB','GB','TB'][log])

def load_from_file(filename):
    return [package.strip('\r\n') for package in open(filename).readlines()]

def list_folder_apks(folder):
    """
    List apks in the given folder
    """
    list_of_apks = [filename for filename in os.listdir(folder) if filename.endswith(".apk")]
    return list_of_apks
