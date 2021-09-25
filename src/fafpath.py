import os
import sys

__all__ = ["get_srcdir", "get_resdir", "get_libdir"]

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


def get_srcdir():
    if not run_from_source():
        return None
    else:
        return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def get_resdir():
    if run_from_frozen():
        # On Windows the res dir is relative to the executable
        return os.path.join(os.path.dirname(sys.executable), "res")
    elif run_from_unix_install():
        return UNIX_SHARE_PATH
    else:
        # We are most likely running from source
        return os.path.join(get_srcdir(), "res")


def get_libdir():
    """
    Get the directory where our own additional executables live. Returns None
    if there is no such directory (ex. we run on linux and have everything
    installed in PATH already).
    """
    if run_from_frozen():
        # lib dir should be where our executable lives
        return os.path.join(os.path.dirname(sys.executable), "lib")
    elif run_from_unix_install():
        # Everything should be in PATH
        return None
    else:
        # We are most likely running from source
        return os.path.join(get_srcdir(), "lib")


def get_java_path():
    return os.path.join(get_libdir(), "ice-adapter", "jre", "bin", "java.exe")
