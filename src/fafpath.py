import os
import sys

__all__ = ["get_resdir"]

# default unix res path
UNIX_SHARE_PATH = '/usr/share/fafclient'

def run_from_frozen():
    return getattr(sys, 'frozen', False)

def run_from_unix_install():
    local_res = os.path.join(os.getcwd(), "res")
    return not run_from_frozen() and sys.platform != 'win32' and not os.path.exists(local_res)

def get_resdir():
    if run_from_frozen():
        # On Windows the res dir is relative to the executable or main.py script
        return os.path.join(os.path.dirname(sys.executable), "res")
    elif run_from_unix_install():
        return UNIX_SHARE_PATH
    else:
        # We are most likely running from source
        srcDir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(os.path.dirname(srcDir), "res")

def get_userdir():
    # These directories are in Appdata (e.g. C:\ProgramData on some Win7 versions)
    if 'ALLUSERSPROFILE' in os.environ:
        return os.path.join(os.environ['ALLUSERSPROFILE'], "FAForever")
    else:
        return os.path.join(os.environ['HOME'], "FAForever")
