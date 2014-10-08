from PyQt4.QtCore import pyqtSlot
import bsdiff4
import pytest
import os
import pygit2
import binary
import sys

__author__ = 'Thygrrr'


def test_copy_rename_copies_all_files(tmpdir, application):
    source_dir = tmpdir.mkdir("source")
    dest_dir = tmpdir.mkdir("dest")

    source_dir.join("a").write("a")
    source_dir.join("b").write("b")

    copy_table = {"a":None, "b":None}

    updater = binary.Updater(application)
    updater.copy_rename(copy_table, str(source_dir), str(dest_dir))
    assert dest_dir.join("a").exists()
    assert dest_dir.join("b").exists()


def test_copy_rename_renames_files(tmpdir, application):
    source_dir = tmpdir.mkdir("source")
    dest_dir = tmpdir.mkdir("dest")

    source_dir.join("a").write("a")

    copy_table = {"a":"b"}

    updater = binary.Updater(application)
    updater.copy_rename(copy_table, str(source_dir), str(dest_dir))
    assert dest_dir.join("b").exists()
    assert dest_dir.join("b").read() == "a"


def test_copy_rename_emits_all_progress_updates(tmpdir, application, signal_receiver):
    source_dir = tmpdir.mkdir("source")
    dest_dir = tmpdir.mkdir("dest")

    source_dir.join("a").write("a")
    source_dir.join("b").write("b")

    copy_table = {"a":None, "b":None}

    updater = binary.Updater(application)
    updater.progress_value.connect(signal_receiver.int_slot)
    updater.copy_rename(copy_table, str(source_dir), str(dest_dir))

    assert signal_receiver.int_values[0] == 1
    assert signal_receiver.int_values[1] == 2


def test_copy_rename_emits_correct_number_of_progress_updates(tmpdir, application, signal_receiver):
    source_dir = tmpdir.mkdir("source")
    dest_dir = tmpdir.mkdir("dest")

    source_dir.join("a").write("a")

    copy_table = {"a":None}

    updater = binary.Updater(application)
    updater.progress_value.connect(signal_receiver.int_slot)
    updater.copy_rename(copy_table, str(source_dir), str(dest_dir))

    assert len(signal_receiver.int_values) == 1


def test_guess_install_guesses_steam_if_steam_dll_exists(tmpdir):
    tmpdir.join("steam_api.dll").write("I'm steam!")
    assert binary.Updater.guess_install_type(str(tmpdir)) == 'steam'


def test_guess_install_guesses_retail_if_no_steam_dll_exists(tmpdir):
    assert binary.Updater.guess_install_type(str(tmpdir)) == 'retail'


def test_patch_directory_contents_patches_files(tmpdir, application):
    import hashlib
    tmpdir.join("a").write("b")
    patchdir = tmpdir.mkdir("patches")
    patchdir.join(hashlib.md5("b").hexdigest()).write(bsdiff4.diff("b", "c"), "wb")
    post_patch_verify = {"a": hashlib.md5("c").hexdigest()}
    updater = binary.Updater(application)
    updater.patch_directory_contents(post_patch_verify, str(patchdir), str(tmpdir))
    assert tmpdir.join("a").read() == "c"


def test_patch_directory_contents_raises_patch_failed_on_signature_mismatch(tmpdir, application):
    with pytest.raises(binary.PatchFailedError):
        import hashlib
        tmpdir.join("a").write("b")
        patchdir = tmpdir.mkdir("patches")
        patchdir.join(hashlib.md5("b").hexdigest()).write(bsdiff4.diff("b", "c"), "wb")
        post_patch_verify = {"a": hashlib.md5("won't match").hexdigest()}
        updater = binary.Updater(application)
        updater.patch_directory_contents(post_patch_verify, str(patchdir), str(tmpdir))


def test_patch_directory_contents_does_not_touch_files_without_patch(tmpdir, application):
    import hashlib
    tmpdir.join("a").write("a")
    patchdir = tmpdir.mkdir("patches")
    post_patch_verify = {"a": hashlib.md5("a").hexdigest()}
    updater = binary.Updater(application)
    updater.patch_directory_contents(post_patch_verify, str(patchdir), str(tmpdir))
    assert tmpdir.join("a").read() == "a"


def test_patch_directory_contents_raises_patch_failed_on_mismatching_untouched_file(tmpdir, application):
    with pytest.raises(binary.PatchFailedError):
        import hashlib
        tmpdir.join("a").write("a")
        patchdir = tmpdir.mkdir("patches")
        post_patch_verify = {"a": hashlib.md5("won't match").hexdigest()}
        updater = binary.Updater(application)
        updater.patch_directory_contents(post_patch_verify, str(patchdir), str(tmpdir))

