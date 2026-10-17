@echo off
setlocal
set "CARNIVAL_ROOT=%~dp0.."
where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo Windows PowerShell was not found. See docs\DELIVERY.md.
  pause
  exit /b 1
)
powershell.exe -NoLogo -NoProfile -Command "$ErrorActionPreference = 'Stop'; $root = $env:CARNIVAL_ROOT; $manifest = Get-Content -LiteralPath (Join-Path $root 'blender/source_parts.json') -Raw | ConvertFrom-Json; $target = Join-Path $root $manifest.output; if (Test-Path -LiteralPath $target) { if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower() -eq $manifest.sha256) { Write-Host ('Already verified: ' + $target); exit 0; }; throw ('Refusing to overwrite a different existing file: ' + $target); }; $temp = $target + '.assembling'; if (Test-Path -LiteralPath $temp) { throw ('Temporary file already exists. Review it before retrying: ' + $temp) }; $stream = $null; try { $stream = [System.IO.File]::Open($temp, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write); foreach ($part in $manifest.parts) { $path = Join-Path $root $part.path; if ((Get-Item -LiteralPath $path).Length -ne $part.bytes) { throw ('Wrong chunk length: ' + $path) }; if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower() -ne $part.sha256) { throw ('Wrong chunk hash: ' + $path) }; $inputStream = [System.IO.File]::OpenRead($path); try { $inputStream.CopyTo($stream) } finally { $inputStream.Dispose() }; }; $stream.Dispose(); $stream = $null; if ((Get-Item -LiteralPath $temp).Length -ne $manifest.bytes) { throw 'Complete file length mismatch' }; if ((Get-FileHash -LiteralPath $temp -Algorithm SHA256).Hash.ToLower() -ne $manifest.sha256) { throw 'Complete file checksum mismatch' }; [System.IO.File]::Move($temp, $target); Write-Host ('Verified Blender source: ' + $target); } finally { if ($null -ne $stream) { $stream.Dispose() }; }"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Reassembly failed. Read the error above; your existing source was not overwritten.
pause
exit /b %RESULT%
