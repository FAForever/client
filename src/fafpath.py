import os
import sys

__all__ = ["get_resdir"]

# default unix res path
UNIX_SHARE_PATH = '/usr/share/fafclient'

def run_from_frozen():
    return getattr(sys, 'frozen', False)

def run_from_source():
    if run_from_frozen():
        return False
    # If we're run from source, we live in a directory called 'src'
    # Very unlikely to be called that if we run an installed FAF
    file_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.basename(file_dir) == 'src'

def run_from_unix_install():
    return not run_from_frozen() and not run_from_source()


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
