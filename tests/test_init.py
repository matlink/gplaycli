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

def test_connection_token():
    gpc.token = True
    gpc.token = gpc.retrieve_token(token_url)
    gpc.token_url = token_url
    success, error = gpc.connect_to_googleplay_api()
    assert error is None
    assert success == True

def test_connection_credentials():
    gpc.token = False
    gpc.config['gmail_address']  = os.environ['GMAIL_ADDR']
    gpc.config['gmail_password'] = os.environ['GMAIL_PWD']
    success, error = gpc.connect_to_googleplay_api()
    assert error is None
    assert success == True

def test_download_duckduckgo():
    gpc.progress_bar = True
    gpc.config['download_folder_path'] = os.path.abspath('.')
    gpc.download_packages(['com.duckduckgo.mobile.android'])
