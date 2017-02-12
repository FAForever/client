# -*- coding: utf-8 -*-
# Authors: Douglas Creager <dcreager@dcreager.net> and Moritz Voss
# This file is placed into the public domain.

# Calculates the current version number. The version number can come from
# two sources - returned by git (the output of “git describe”, modified
# to conform to the versioning scheme that setuptools uses) or read from
# the RELEASE-VERSION file.
#
# Two functions are provided for reading the version - get_release_version
# and get_git_version. The earlier is used by FAF to read the version
# at runtime, the other is used by setup scripts.
#
# There is also a function that allows you to write version information,
# write_version_file. It accepts a string to write and the directory you
# want to create the version file in.
#
# Finally, you can run this file with an interpreter. It will simply return
# the output of get_git_version. If it fails to find the version, the return
# value will be 1.
#
# Note that the RELEASE-VERSION file should *not* be checked into git;
# please add it to your top-level .gitignore file.

from subprocess import check_output
import sys, os

__all__ = ["get_git_version", "get_release_version", "write_version_file"]

def is_development_version(version):
    return "-" in version and not is_prerelease_version(version)

def is_prerelease_version(version):
    return "pre" in version or "rc" in version

def version_filename(dir):
    return os.path.join(dir, "RELEASE-VERSION")

def read_version_file(dir):
    try:
        f = open(version_filename(dir), "r")

        try:
            version = f.readlines()[0]
            return version.strip()

        finally:
            f.close()

    except IOError:
        return None


def write_version_file(version, dir):
    with open(version_filename(dir), "w") as f:
        f.write("%s\n" % version)


def msi_version(git_version):
    import re
    sanitized = [fragment for fragment in re.findall(r"[\w']+", git_version) if fragment.isdigit()][:3]
    return ".".join(sanitized) or "0.0.0"


def get_git_version(git_dir = None):
    git_args = ['describe', '--tags', '--always']
    if git_dir is not None:
        git_args = ['-C', git_dir] + git_args
    try:
        lines = check_output(["git"] + git_args).split(os.linesep)
        line = lines[0]
        return line
    except Exception as e:
        sys.stderr.write("Error grabbing git version: {}".format(e))
        return None

def get_release_version(dir = None, git_dir = None):
    version = read_version_file(dir) if dir is not None else None
    if version is not None:
        return version

    # Maybe we are running from source?
    version = get_git_version(git_dir)
    # If we still don't have anything, that's an error.
    if version is None:
        sys.stderr.write("Could not get git version" + os.linesep)
        raise ValueError("Cannot find the version number! Please provide RELEASE-VERSION file or run from git.")
    return version

if __name__ == "__main__":
    res = get_git_version()
    if res is None:
        exit(1)
    print(res)
