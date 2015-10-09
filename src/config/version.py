# -*- coding: utf-8 -*-
# Authors: Douglas Creager <dcreager@dcreager.net> and Moritz Voss
# This file is placed into the public domain.

# Calculates the current version number.  If possible, this is the
# output of “git describe”, modified to conform to the versioning
# scheme that setuptools uses.  If “git describe” returns an error
# (most likely because we're in an unpacked copy of a release tarball,
# rather than in a git working copy), then we fall back on reading the
# contents of the RELEASE-VERSION file.
#
# To use this script, simply import it your setup.py file, and use the
# results of get_git_version() as your package version:
#
# from version import *
#
# setup(
# version=get_git_version(),
#     .
#     .
#     .
# )
#
# This will automatically create and update a RELEASE-VERSION file that can
# be bundled with  your distributable. If one exists, it will read that.
# Note that the RELEASE-VERSION file should *not* be checked into git;
# please add it to your top-level .gitignore file.

from subprocess import Popen, PIPE

__all__ = "get_git_version"

def call_git_describe():
    try:
        p = Popen(['git', 'describe', '--tags'],
                  stdout=PIPE, stderr=PIPE)
        p.stderr.close()
        line = p.stdout.readlines()[0]
        return line.strip()
    except Exception as e:
        print("Error grabbing git version: {}".format(e))
        return "0.0-pre"

def is_development_version(version):
    return "-" in version and not is_prerelease_version(version)


def is_prerelease_version(version):
    return "pre" in version or "rc" in version

def read_release_version():
    try:
        f = open("RELEASE-VERSION", "r")

        try:
            version = f.readlines()[0]
            return version.strip()

        finally:
            f.close()

    except IOError:
        return None


def write_release_version(version):
    with open("RELEASE-VERSION", "w") as f:
        f.write("%s\n" % version)


def msi_version(git_version):
    import re
    sanitized = [fragment for fragment in re.findall(r"[\w']+", git_version) if fragment.isdigit()][:3]
    return ".".join(sanitized) or "0.0.0"


def get_git_version():
    # Read in the version that's currently in RELEASE-VERSION.
    release_version = read_release_version()

    # First try to get the current version using “git describe”.
    version = call_git_describe()

    # If that doesn't work, fall back on the value that's in
    # RELEASE-VERSION.

    if version is None:
        version = release_version

    # If we still don't have anything, that's an error.

    if version is None:
        raise ValueError("Cannot find the version number!")

    # Finally, return the current version.
    return version


if __name__ == "__main__":
    print get_git_version()
