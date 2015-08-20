$BASE_URL = "https://www.python.org/ftp/python/"
$GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
$GET_PIP_PATH = "C:\get-pip.py"

$webclient = (new-object net.webclient)

$python_home = "C:\Python27"

$pip_path = $python_home + "\Scripts\pip.exe"
$python_path = $python_home + "\python.exe"

if (-not(Test-Path $pip_path)) {
  Write-Host "Installing pip..."
  $webclient = New-Object System.Net.WebClient
  $webclient.DownloadFile($GET_PIP_URL, $GET_PIP_PATH)
  Write-Host "Executing:" $python_path $GET_PIP_PATH
  Start-Process -FilePath "$python_path" -ArgumentList "$GET_PIP_PATH" -Wait -Passthru
} else {
  Write-Host "pip already installed."
}

function InstallPackage ($pkg) {
    & $pip_path install $pkg
}

InstallPackage http://content.faforever.com/wheel/lupa-1.1-cp27-none-win32.whl
InstallPackage wheel
InstallPackage pytest
InstallPackage cffi
InstallPackage cx_Freeze

& $pip_path install -r requirements.txt
