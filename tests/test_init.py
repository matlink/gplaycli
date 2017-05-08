import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from gplaycli import gplaycli
gpc = gplaycli.GPlaycli()

token_url = "https://matlink.fr/token/email/gplaycliacc@gmail.com"

def test_default_settings():
    assert gpc.yes == False
    assert gpc.verbose == False
    assert gpc.progress_bar == False

def test_connection():
    gpc.token = True
    gpc.retrieve_token(token_url)
    success, error = gpc.connect_to_googleplay_api()
    assert error is None
    assert success == True

def test_download_firefox():
    gpc.download_packages(['org.mozilla.firefox'])
