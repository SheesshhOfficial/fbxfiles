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
$archive = 'You_want_it_You_get_it_Exterior_v2_Source_and_Overlay.zip'
$expected = '8cf48a5173b2c97bb70b2af3dc1625a163029f5c985cd6ae7fd1e6c91fa63112'
$expectedLength = 60266914
$parts = @(
    @{ Name = 'You_want_it_You_get_it_Exterior_v2_Source_and_Overlay.zip.part01'; Length = 9437184; Hash = '1f167f060628559afc76fa69c4fcc13f27719b021e0c2302266e9d9824674ed4' },
    @{ Name = 'You_want_it_You_get_it_Exterior_v2_Source_and_Overlay.zip.part02'; Length = 9437184; Hash = '97498b013819ddd7940658bd357f07a2705665e6a381b74035af90ade76a9358' },
    @{ Name = 'You_want_it_You_get_it_Exterior_v2_Source_and_Overlay.zip.part03'; Length = 9437184; Hash = '1e78a6df600040205eeddbc0299e94b363fbc764f139d5575105a95cc79ca609' },
    @{ Name = 'You_want_it_You_get_it_Exterior_v2_Source_and_Overlay.zip.part04'; Length = 9437184; Hash = '474b90b3bf0af49e0cb18035e39784b8c27ec9007fa7ceb72d0231acbe229d4e' },
    @{ Name = 'You_want_it_You_get_it_Exterior_v2_Source_and_Overlay.zip.part05'; Length = 9437184; Hash = 'a1ce55232b8304a9f5428a6d821b3d40484fb9c55b146a1c4ca68d0e1b57bf63' },
    @{ Name = 'You_want_it_You_get_it_Exterior_v2_Source_and_Overlay.zip.part06'; Length = 9437184; Hash = '2a93ca6e0bed80998ab1aafb2b6e20c9c03893f5640351c444327fe53da30762' },
    @{ Name = 'You_want_it_You_get_it_Exterior_v2_Source_and_Overlay.zip.part07'; Length = 3643810; Hash = 'a755dca8d40b30bf169d08c65d29958dbe102fafa86410a237d17d60c247be0a' }
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
