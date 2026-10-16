@echo off
setlocal
cd /d "%~dp0"
set "OUT=SnipersAim_Dense_Canyon_v2.blend"
set "TMP=SnipersAim_Dense_Canyon_v2.blend.reassembling"
if exist "%OUT%" (
  certutil -hashfile "%OUT%" SHA256 | findstr /I /C:"6d9df542034455e209ba8a790d83afbe41f4c95f878e5789d725425bb029b123" >nul
  if errorlevel 1 (
    echo A different Blender file already exists. Move or rename it first.
    exit /b 1
  )
  echo Blender file already exists and its SHA256 is correct.
  exit /b 0
)
if exist "%TMP%" (
  echo A temporary file already exists. Inspect or move it first: %TMP%
  exit /b 1
)
if not exist "SnipersAim_Dense_Canyon_v2.001.part" (
  echo Missing part: SnipersAim_Dense_Canyon_v2.001.part. Pull the repository again.
  exit /b 1
)
certutil -hashfile "SnipersAim_Dense_Canyon_v2.001.part" SHA256 | findstr /I /C:"18572459f35bd38b4ea830d2c5de26825bc9ea95fffb592de10c6d5c48d38832" >nul
if errorlevel 1 (
  echo Checksum mismatch: SnipersAim_Dense_Canyon_v2.001.part
  exit /b 1
)if not exist "SnipersAim_Dense_Canyon_v2.002.part" (
  echo Missing part: SnipersAim_Dense_Canyon_v2.002.part. Pull the repository again.
  exit /b 1
)
certutil -hashfile "SnipersAim_Dense_Canyon_v2.002.part" SHA256 | findstr /I /C:"1c3ee1236b8c094cd696b5565d3ec846f7a46a5f15c723149263ce0045be9473" >nul
if errorlevel 1 (
  echo Checksum mismatch: SnipersAim_Dense_Canyon_v2.002.part
  exit /b 1
)if not exist "SnipersAim_Dense_Canyon_v2.003.part" (
  echo Missing part: SnipersAim_Dense_Canyon_v2.003.part. Pull the repository again.
  exit /b 1
)
certutil -hashfile "SnipersAim_Dense_Canyon_v2.003.part" SHA256 | findstr /I /C:"3a133952e1112f33211af5779ed272d70e79022c700b835b30735acfba1e05e5" >nul
if errorlevel 1 (
  echo Checksum mismatch: SnipersAim_Dense_Canyon_v2.003.part
  exit /b 1
)if not exist "SnipersAim_Dense_Canyon_v2.004.part" (
  echo Missing part: SnipersAim_Dense_Canyon_v2.004.part. Pull the repository again.
  exit /b 1
)
certutil -hashfile "SnipersAim_Dense_Canyon_v2.004.part" SHA256 | findstr /I /C:"bee6fd09f37195a1181219a24fa1ffec83c761777e8fa9a4967d1021c91a7367" >nul
if errorlevel 1 (
  echo Checksum mismatch: SnipersAim_Dense_Canyon_v2.004.part
  exit /b 1
)if not exist "SnipersAim_Dense_Canyon_v2.005.part" (
  echo Missing part: SnipersAim_Dense_Canyon_v2.005.part. Pull the repository again.
  exit /b 1
)
certutil -hashfile "SnipersAim_Dense_Canyon_v2.005.part" SHA256 | findstr /I /C:"28fe7ed527519714e10ea3384c7e58c771050c5282fd0b5652b4256b583002c6" >nul
if errorlevel 1 (
  echo Checksum mismatch: SnipersAim_Dense_Canyon_v2.005.part
  exit /b 1
)if not exist "SnipersAim_Dense_Canyon_v2.006.part" (
  echo Missing part: SnipersAim_Dense_Canyon_v2.006.part. Pull the repository again.
  exit /b 1
)
certutil -hashfile "SnipersAim_Dense_Canyon_v2.006.part" SHA256 | findstr /I /C:"047a53660d44e9d98495a4220eab1d678ee455ab6bc33ccc8e32c52527f2d34f" >nul
if errorlevel 1 (
  echo Checksum mismatch: SnipersAim_Dense_Canyon_v2.006.part
  exit /b 1
)if not exist "SnipersAim_Dense_Canyon_v2.007.part" (
  echo Missing part: SnipersAim_Dense_Canyon_v2.007.part. Pull the repository again.
  exit /b 1
)
certutil -hashfile "SnipersAim_Dense_Canyon_v2.007.part" SHA256 | findstr /I /C:"c9d0c362af1efe4fb3ef0d549737cc2fd6d0fea81aea5e650e4d6ad62ada2261" >nul
if errorlevel 1 (
  echo Checksum mismatch: SnipersAim_Dense_Canyon_v2.007.part
  exit /b 1
)if not exist "SnipersAim_Dense_Canyon_v2.008.part" (
  echo Missing part: SnipersAim_Dense_Canyon_v2.008.part. Pull the repository again.
  exit /b 1
)
certutil -hashfile "SnipersAim_Dense_Canyon_v2.008.part" SHA256 | findstr /I /C:"9cabcae6d95cf8599439058c4ca43b3defe2a1261c98a6eb6097ca26e3f07016" >nul
if errorlevel 1 (
  echo Checksum mismatch: SnipersAim_Dense_Canyon_v2.008.part
  exit /b 1
)copy /b "SnipersAim_Dense_Canyon_v2.001.part"+"SnipersAim_Dense_Canyon_v2.002.part"+"SnipersAim_Dense_Canyon_v2.003.part"+"SnipersAim_Dense_Canyon_v2.004.part"+"SnipersAim_Dense_Canyon_v2.005.part"+"SnipersAim_Dense_Canyon_v2.006.part"+"SnipersAim_Dense_Canyon_v2.007.part"+"SnipersAim_Dense_Canyon_v2.008.part" "%TMP%" >nul
if errorlevel 1 exit /b 1
certutil -hashfile "%TMP%" SHA256 | findstr /I /C:"6d9df542034455e209ba8a790d83afbe41f4c95f878e5789d725425bb029b123" >nul
if errorlevel 1 (
  echo Final checksum mismatch. Temporary file retained for inspection.
  exit /b 1
)
if exist "%OUT%" (
  echo Output appeared during reassembly. Refusing to overwrite it.
  exit /b 1
)
move /-Y "%TMP%" "%OUT%" >nul
if errorlevel 1 exit /b 1
echo Created and SHA256-verified: %OUT%
