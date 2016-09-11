$BASE_URL = "https://www.python.org/ftp/python/"
$GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
$GET_PIP_PATH = "C:\get-pip.py"

$webclient = (new-object net.webclient)

$python_home = "C:\Python34"

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
InstallPackage https://pypi.python.org/packages/68/76/c3457dfe31c5a6c4fc3687d012a89c769d52129f19584415309aa0339a31/pypiwin32-219-cp34-none-win32.whl#md5=d1064ebb932294271b883ffdb369c640
InstallPackage cx_Freeze

& $pip_path install -r requirements.txt
