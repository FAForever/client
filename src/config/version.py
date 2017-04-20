# -*- coding: utf-8 -*-
# Authors: Douglas Creager <dcreager@dcreager.net> and Moritz Voss
# Modified by: Igor Kotrasinski <ikotrasinsk@gmail.com>
# This file is placed into the public domain.

# Calculates the current version number. The version number can come from
# two sources - returned by git (last version tag and commit hash as given
# by git-describe) or read from the RELEASE-VERSION file.
#
# The format of the version number is:
#
# Major.Minor.Patch[-rc.Prerelease]+[Git_revision.]Build_id
#
# The function get_git_version is used by setup scripts to read the version
# (part before '+') and optional git revision. Build id comes from various
# sources (appveyor, setup.py, this file if FAF is run from git).
#
# Function 'build_version' can be used to assemble the full version from the
# version, revision and build id. You can omit the build id to get a partial
# version number without the build id (e.g. for an external build system).
#
# Function 'write_version_file' allows you to write version information.
# It accepts a string to write and the directory you want to create the
# version file in.
#
# Finally, you can run this file with an interpreter. It will print the
# version string suitable for appending with the build number. If it fails
# to find the version, the return value will be 1.
#
# Note that the RELEASE-VERSION file should *not* be checked into git;
# please add it to your top-level .gitignore file.

from subprocess import check_output
import sys, os
from semantic_version import Version

__all__ = ["is_development_version", "is_prerelease_version",
           "get_git_version", "build_version", "get_release_version", "write_version_file"]

def is_development_version(version):
    # We're on a dev build if metadata has more items than just a build id
    build = Version(version).build
    return build is not None and len(build) >= 2

def is_prerelease_version(version):
    return Version(version).prerelease is not None


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


def get_git_version(git_dir = None):

    def get_cmd_line(cmd):
        lines = check_output(cmd).decode().split(os.linesep)
        line = lines[0]
        return line

    git_args = ['describe', '--tags', '--always']
    if git_dir is not None:
        git_args = ['-C', git_dir] + git_args

    try:
        # Get tag only first
        tag = get_cmd_line(["git"] + git_args + ["--abbrev=0"])
        # Now tag with commit info appended
        version = get_cmd_line(["git"] + git_args)

        # Strip leading hyphen
        commit_tag = version[len(tag) + 1:]

        return (tag, commit_tag)

    except Exception as e:
        sys.stderr.write("Error grabbing git version: {}".format(e))
        return None

def build_version(version, revision, build = None):
    return version + '+' + \
           (revision + '.' if revision else '') + \
           (build if build else '')

# Distutils expect an x.y.z (non-semver) format
def msi_version(version):
    nopre_v = Version(version)
    nopre_v.prerelease = None
    return str(nopre_v)

# Used by FAF to read the version at runtime
def get_release_version(dir = None, git_dir = None):
    version = read_version_file(dir) if dir is not None else None
    if version is not None:
        return version

    # Maybe we are running from source?
    git_version = get_git_version(git_dir)
    if git_version is not None:
        return build_version(*git_version, build = "git")
    else:
        # If we still don't have anything, that's an error.
        sys.stderr.write("Could not get git version" + os.linesep)
        raise ValueError("Cannot find the version number! Please provide RELEASE-VERSION file or run from git.")


if __name__ == "__main__":
    res = get_git_version()
    if res is None:
        exit(1)
    print(build_version(*res))
