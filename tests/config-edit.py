import os
import sys

addr = os.environ['GMAIL_ADDR']
pwd  = os.environ['GMAIL_PWD']

filename = sys.argv[1]
config = open(filename).read()
config = config.replace('gmail_address=', 'gmail_address=' + addr).replace('gmail_password=', 'gmail_password=' + pwd)
print(config, file=open(filename, 'w'))