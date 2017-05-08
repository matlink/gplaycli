import sys
import os

sys.path.insert(0, os.path.abspath('.'))

def test_default_settings():
    from gplaycli import gplaycli
    gpc = gplaycli.GPlaycli()
    assert gpc.yes == False
    assert gpc.verbose == False
    assert gpc.progress_bar == False
