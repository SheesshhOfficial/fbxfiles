@echo off
setlocal
set "EVERGREEN_JOIN_FILE=%~f0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -Command "$s=[IO.File]::ReadAllText($env:EVERGREEN_JOIN_FILE); & ([ScriptBlock]::Create(($s -split '(?m)^# POWERSHELL_PAYLOAD\r?$',2)[1]))"
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo Reassembly failed. Read the error above. No existing ZIP was overwritten.
pause
exit /b %RESULT%
# POWERSHELL_PAYLOAD
# Built-in Windows PowerShell 5.1; no Python, installation or policy changes.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$root = [IO.Path]::GetDirectoryName($env:EVERGREEN_JOIN_FILE)
$archive = 'You_Want_It_You_Get_It_Rebuild_Dependencies_v1.zip'
$expected = '3dca6e6009434ed19b332a529e930d8e8abb5029afccdd7bb10d455388319a6c'
$expectedLength = 16669939
$parts = @(
    @{ Name = 'You_Want_It_You_Get_It_Rebuild_Dependencies_v1.zip.part01'; Length = 9437184; Hash = '4e49096db7f2ec178fa5dcc6c59cb893dbf60140998f27ba62409beac8d1fa0e' },
    @{ Name = 'You_Want_It_You_Get_It_Rebuild_Dependencies_v1.zip.part02'; Length = 7232755; Hash = '2ca587686bff144153e435ed80a4e0c1c7451318ab7b0a5e9303f79d568a5047' }
)
$temp = $null
$outputStream = $null
function Test-ExpectedFile($path, $length, $hash) {
    if (-not [IO.File]::Exists($path)) { throw "Missing file: $path" }
    $info = Get-Item -LiteralPath $path
    if ($info.Length -ne $length) { throw "Wrong file size: $path" }
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($actual -ne $hash) { throw "SHA-256 mismatch: $path" }
}
try {
    Write-Host 'Checking all archive parts...'
    foreach ($part in $parts) {
        $path = Join-Path $root $part.Name
        Test-ExpectedFile $path $part.Length $part.Hash
        Write-Host ('OK: ' + $part.Name)
    }
    $destination = Join-Path $root $archive
    if ([IO.File]::Exists($destination)) {
        Test-ExpectedFile $destination $expectedLength $expected
        Write-Host 'The existing ZIP is already correct; it was not changed.'
    } else {
        if ([IO.Directory]::Exists($destination)) { throw "A directory already uses the ZIP name: $destination" }
        $temp = $destination + '.joining.' + [Guid]::NewGuid().ToString('N')
        $outputStream = [IO.File]::Open($temp, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            foreach ($part in $parts) {
                $inputStream = [IO.File]::OpenRead((Join-Path $root $part.Name))
                try { $inputStream.CopyTo($outputStream) } finally { $inputStream.Dispose() }
            }
        } finally { $outputStream.Dispose(); $outputStream = $null }
        Test-ExpectedFile $temp $expectedLength $expected
        # Two-argument Move refuses to replace a destination created meanwhile.
        [IO.File]::Move($temp, $destination)
        $temp = $null
    }
    Write-Host ''
    Write-Host ('VERIFIED: ' + $destination) -ForegroundColor Green
    Write-Host 'Right-click the ZIP, choose Extract All, then open the included README.md.'
    exit 0
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    if ($null -ne $outputStream) { $outputStream.Dispose() }
    if ($null -ne $temp -and [IO.File]::Exists($temp)) {
        try { [IO.File]::Delete($temp) } catch { Write-Host ('Temporary file remains: ' + $temp) }
    }
    exit 1
}
