import argparse
import fileinput
import os
import re
import shutil
from typing import NamedTuple

import scipy

SCIPY_IMPORT_RE = re.compile(r"(\s+)?(from|import) scipy")


class Directory(NamedTuple):
    name: str
    files: tuple[str, ...] = tuple()
    subdirs: tuple[Directory, ...] = tuple()
    empty_init: bool = False


MINIMAL_STRUCTURE = Directory(
    name="scipy_ndimage",
    subdirs=(
        Directory(
            name="_lib",
            files=(
                "__init__.py",
                "_array_api.py",
                "_array_api_override.py",
                "_docscrape.py",
                "_sparse.py",
                "_util.py",
                "doccer.py",
            ),
            empty_init=True,
        ),
        Directory(
            name="_external",
            files=("_array_api_compat_vendor.py",),
            subdirs=(
                Directory(
                    name="array_api_compat",
                    files=(
                        "__init__.py",
                        "_internal.py",
                    ),
                    subdirs=(
                        Directory(
                            name="common",
                            files=(
                                "__init__.py",
                                "_aliases.py",
                                "_fft.py",
                                "_helpers.py",
                                "_linalg.py",
                                "_typing.py",
                            ),
                        ),
                        Directory(
                            name="numpy",
                            files=(
                                "__init__.py",
                                "_aliases.py",
                                "_info.py",
                                "_typing.py",
                                "fft.py",
                                "linalg.py",
                            ),
                            empty_init=True,
                        ),
                    ),
                ),
                Directory(
                    name="array_api_extra",
                    files=(
                        "__init__.py",
                        "testing.py",
                    ),
                    empty_init=True,
                    subdirs=(
                        Directory(
                            name="_lib",
                            files=("__init__.py",),
                            empty_init=True,
                            subdirs=(
                                Directory(
                                    name="_utils",
                                    files=(
                                        "__init__.py",
                                        "_compat.py",
                                        "_helpers.py",
                                        "_typing.py",
                                    ),
                                    empty_init=True,
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        Directory(
            name="ndimage",
            files=(
                "__init__.py",
                "_filters.py",
                "_nd_image",
                "_ni_docstrings.py",
                "_ni_support.py",
                "_rank_filter",
            ),
            empty_init=True,
        ),
    ),
)


def copy_dir(src: str, dr: Directory, dst: str) -> None:
    print(f"Copying directory {dr.name!r} from {src!r} to {dst!r}...")
    print(f"Creating directory {dst!r}...")
    os.makedirs(dst, exist_ok=True)
    for file in dr.files:
        src_file = os.path.join(src, file)
        if os.path.exists(src_file):
            dest_file = os.path.join(dst, file)
            if file == "__init__.py" and dr.empty_init:
                print(f"Creating empty file {dest_file!r}...")
                open(dest_file, "w").close()
            else:
                print(f"Copying file from {src_file!r} to {dest_file!r}...")
                shutil.copyfile(src_file, dest_file)
        else:
            for f in os.listdir(src):
                if f.startswith(file) and (f.endswith(".pyd") or f.endswith(".so")):
                    src_file = os.path.join(src, f)
                    dest_file = os.path.join(dst, f)
                    print(f"Copying file from {src_file!r} to {dest_file!r}...")
                    shutil.copyfile(src_file, dest_file)
                    break
    for subdir in dr.subdirs:
        subsource = os.path.join(src, subdir.name)
        subdest = os.path.join(dst, subdir.name)
        copy_dir(subsource, subdir, subdest)


def replace_imports(module_name: str, root: str, dr: Directory) -> None:
    for file in dr.files:
        if file in (
            "_util.py",
            "_filters.py",
            "_ni_docstrings.py",
            "_array_api.py",
            "_array_api_compat_vendor.py",
            "_array_api_override.py",
        ):
            path = os.path.join(root, file)
            print(f"Replacing imports in {path!r}...")
            with fileinput.input(path, inplace=True, encoding="utf-8") as fi:
                for line in fi:
                    if m := SCIPY_IMPORT_RE.search(line):
                        print(line.replace(f"{m[2]} scipy", f"{m[2]} {module_name}"), end="")
                    else:
                        print(line, end="")
    for subdir in dr.subdirs:
        subroot = os.path.join(root, subdir.name)
        replace_imports(module_name, subroot, subdir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", required=True)
    args = parser.parse_args()

    scipy_loc, = scipy.__spec__.submodule_search_locations
    copy_dir(scipy_loc, MINIMAL_STRUCTURE, args.directory)
    print("Finished copying files.")

    replace_imports(args.directory, args.directory, MINIMAL_STRUCTURE)
    print("Finished minimizing scipy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
