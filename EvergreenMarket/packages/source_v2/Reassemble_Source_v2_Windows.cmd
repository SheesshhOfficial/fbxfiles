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
$archive = 'Evergreen_Market_Source_v2_Complete.zip'
$expected = '21c85917a12ca5709215783ed4e02522ad942c652ac76927525e030c920cdbab'
$expectedLength = 53216166
$parts = @(
    @{ Name = 'Evergreen_Market_Source_v2_Complete.zip.part01'; Length = 9437184; Hash = '9cbef229356e9e29bce3fb9c4345d74865b92b819ed71c3118f6816529c6d373' },
    @{ Name = 'Evergreen_Market_Source_v2_Complete.zip.part02'; Length = 9437184; Hash = '5d0f0a18ef9790120bc7eded300a0a03ddad1cf3454fe684d0bf578fed935983' },
    @{ Name = 'Evergreen_Market_Source_v2_Complete.zip.part03'; Length = 9437184; Hash = 'ae5b207f1639ba84d4b8df3db859a36f990bde177e2b90d581a52ead82284fbd' },
    @{ Name = 'Evergreen_Market_Source_v2_Complete.zip.part04'; Length = 9437184; Hash = '649480c512040892949b9c7cbe5c8ffeb7d4db0cfec5cea5cc92175e6e911831' },
    @{ Name = 'Evergreen_Market_Source_v2_Complete.zip.part05'; Length = 9437184; Hash = 'c586802d55b9812487a57dcf2cb24ef64f0929c4b7550b174504f35bd82d5356' },
    @{ Name = 'Evergreen_Market_Source_v2_Complete.zip.part06'; Length = 6030246; Hash = '1db2ef26031cb938d03b2d9c440c06976e36d7fdf9995177b962124facd9ba73' }
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
    Write-Host 'Right-click the ZIP, choose Extract All, then open the extracted START_HERE.md.'
    exit 0
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    if ($null -ne $outputStream) { $outputStream.Dispose() }
    if ($null -ne $temp -and [IO.File]::Exists($temp)) {
        try { [IO.File]::Delete($temp) } catch { Write-Host ('Temporary file remains: ' + $temp) }
    }
    exit 1
}
