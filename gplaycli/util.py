import math

def sizeof_fmt(num):
    log = int(math.log(num, 1024))
    return "%.2f%s" % (num/(1024**log), ['bytes','KB','MB','GB','TB'][log])

