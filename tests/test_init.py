import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from gplaycli import gplaycli
gpc = gplaycli.GPlaycli()

token_url = "https://matlink.fr/token/email/gsfid"

def test_default_settings():
    assert gpc.yes == False
    assert gpc.verbose == False
    assert gpc.progress_bar == False
    assert gpc.device_codename == 'bacon'

def test_connection_token():
    gpc.token = True
    gpc.token_url = token_url
    gpc.token, gpc.gsfid = gpc.retrieve_token(token_url, force_new=True)
    success, error = gpc.connect_to_googleplay_api()
    assert error is None
    assert success == True

def test_connection_credentials():
    try: # You are travis
        if os.environ['TRAVIS_PULL_REQUEST'] != "false": # If current job is a Pull Request
            print("Job is pull request. Won't check credentials")
            return
    except KeyError: # You are not travis
        pass
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
