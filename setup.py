import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"include_files": ["res"], "icon": "res/faf.ico"}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="faforever",
    version="0.1",
    description="Forged Alliance Forever!",
    options={"build_exe": build_exe_options},
    executables=[Executable("src/__main__.py", base=base, targetName="FAForever.exe")]
)
