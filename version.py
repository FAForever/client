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


__all__ = "get_git_version"

import pygit2


def git_describe(repository, commit):
    """
    Python equivalent to the git describe --tags command.
    """
    import re
    regex = re.compile('^refs/tags')
    tags = filter(lambda r: regex.match(r), repository.listall_references())

    if tags:
        tag_lookup = {}
        for tag in tags:
            tag_lookup[repository.lookup_reference(tag).resolve().get_object().hex] = tag

        distance = 0
        for parent in repository.walk(commit, pygit2.GIT_SORT_TIME):
            if parent.hex in tag_lookup:
                if distance == 0:
                    return tags[parent.hex]
                return '%s-%d-g%s' % (tag_lookup[parent.hex][10:], distance, commit.hex[:7])
            distance += 1

    return 'g' + commit.hex[:7]


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
    repo = pygit2.Repository(".")
    version = git_describe(repo, repo.head.target)

    # If that doesn't work, fall back on the value that's in
    # RELEASE-VERSION.

    if version is None:
        version = release_version

    # If we still don't have anything, that's an error.

    if version is None:
        raise ValueError("Cannot find the version number!")

    # If the current version is different from what's in the
    # RELEASE-VERSION file, update the file to be current.

    if version != release_version:
        write_release_version(version)

    # Finally, return the current version.
    return version


if __name__ == "__main__":
    print get_git_version()
