import pytest
import py
import os

from git import Repository, Version

__author__ = 'Sheeo'


def test_version_can_be_created():
    version = Version('FAForever/fa', '3634', 'http://github.com/FAForever/fa.git', '791035045345a4c597a92ea0ef50d71fcccb0bb1')
    assert version
    assert version.repo
    assert version.ref
    assert version.url
    assert version.hash


def test_version_with_hash_is_stable():
    assert Version('FAForever/fa', '3634', None, '791035045345a4c597a92ea0ef50d71fcccb0bb1').is_stable


def test_version_without_hash_is_unstable():
    assert Version('FAForever/fa', 'master').is_stable is False


def test_version_without_url_is_trusted():
    assert Version('FAForever/fa', 'master').is_trusted


def test_version_with_default_url_is_trusted():
    assert Version('FAForever/fa', '3634', 'http://github.com/FAForever/fa.git', '791035045345a4c597a92ea0ef50d71fcccb0bb1').is_stable


def test_version_can_be_constructed_from_json():
    version = Version('FAForever/fa', '3634', 'http://github.com/FAForever/fa.git', '791035045345a4c597a92ea0ef50d71fcccb0bb1')
    json_version = Version("""
                   {
                    "repo": "FAForever/fa",
                    "ref": "3634",
                    "url": "http://github.com/FAForever/fa.git",
                    "hash": "791035045345a4c597a92ea0ef50d71fcccb0bb1"
                   }
                   """)
    assert version.hash == json_version.hash
    assert version.repo == json_version.repo
    assert version.ref == json_version.ref
    assert version.url == json_version.url


