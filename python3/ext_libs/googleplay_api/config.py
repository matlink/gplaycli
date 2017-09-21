# separator used by search.py, categories.py, ...
SEPARATOR = ";"

LANG            = "fr_FR" # can be en_US, fr_FR, ...
ANDROID_ID      = "32AA74CDC05B26A9" # "xxxxxxxxxxxxxxxx"
GOOGLE_LOGIN    = "tefuhkog@gmail.com" # "username@gmail.com"
GOOGLE_PASSWORD = "tyuiop65"
AUTH_TOKEN      = None # "yyyyyyyyy"

# force the user to edit this file
if any([each == None for each in [ANDROID_ID, GOOGLE_LOGIN, GOOGLE_PASSWORD]]):
    raise Exception("config.py not updated")

