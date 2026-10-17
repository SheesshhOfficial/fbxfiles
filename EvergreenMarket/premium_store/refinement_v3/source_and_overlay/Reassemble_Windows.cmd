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
$archive = 'You_want_it_You_get_it_Refined_v3_Source_and_Overlay.zip'
$expected = 'bf5e87abd78c4c5916add574b0d2a2999fce89820316d95b5573e701418081b1'
$expectedLength = 47934313
$parts = @(
    @{ Name = 'You_want_it_You_get_it_Refined_v3_Source_and_Overlay.zip.part01'; Length = 9437184; Hash = '38f0fde648122425b9d17a2af9fe924e301980b713f59f09942641e0e228bbd6' },
    @{ Name = 'You_want_it_You_get_it_Refined_v3_Source_and_Overlay.zip.part02'; Length = 9437184; Hash = 'ec0096ccba6c35853e8c7c464dee9240820bb82d99ee10ba9472b0d513fbc28b' },
    @{ Name = 'You_want_it_You_get_it_Refined_v3_Source_and_Overlay.zip.part03'; Length = 9437184; Hash = '2102b1416c4f436d0a6b9f21a6fbc0bd303bf7ba92f0e44a8f3fe33eb773360c' },
    @{ Name = 'You_want_it_You_get_it_Refined_v3_Source_and_Overlay.zip.part04'; Length = 9437184; Hash = '5e6b1f46c87d83ea20bc282d4557f62a0b024b2451e41ccdcc66799c0574d7f9' },
    @{ Name = 'You_want_it_You_get_it_Refined_v3_Source_and_Overlay.zip.part05'; Length = 9437184; Hash = '18750db69806d0ac3dd6cb42f4234f4852035fd0e242335003df7e8e340675e4' },
    @{ Name = 'You_want_it_You_get_it_Refined_v3_Source_and_Overlay.zip.part06'; Length = 748393; Hash = 'c09129479e182be1106f08a67c872330833909b9e215bb010e3e12eea504a372' }
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
