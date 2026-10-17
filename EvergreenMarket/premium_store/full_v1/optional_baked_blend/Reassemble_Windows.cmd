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
$archive = 'FINAL_PACKED_PBR_v1.zip'
$expected = '07137efd92e57e37c59b113c70490bb61cc26c8fa9148162f44c29bea525f7f5'
$expectedLength = 118987569
$parts = @(
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part01'; Length = 9437184; Hash = '221f85e976b06f4b4ee372b1e281e30e5953f4ee87a7e6fcfd13467aae5c7dd3' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part02'; Length = 9437184; Hash = 'fcab47fdace209162c241442b6b76855305b761ea095a9e52a6ae2c67e7ccf30' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part03'; Length = 9437184; Hash = '5445e8355631d7380fd22fd320ee2cdba050fb8ddbfe1d4a5718803e9c1c5ef2' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part04'; Length = 9437184; Hash = '442affb32f3feb7b41011ef0f438e0915ee9d08972cf9ba2d72d5a25df280098' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part05'; Length = 9437184; Hash = '6dfee177eb43d2e2dcf39ac1d7f1ba06aeb7008e6a915319c95480ef46e7b7a8' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part06'; Length = 9437184; Hash = 'c5b33c3fa2213995fbccf2d159f3499ce882f5cc2dfd34d4c11251cfd1428882' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part07'; Length = 9437184; Hash = 'd93128848358d550216b913885be30eb5ca4ddcfb00949502275605de3a73451' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part08'; Length = 9437184; Hash = '726df8f3b6b806e1e03ba47445059308051ec4101939bb57eeaebfeaacb7ab8d' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part09'; Length = 9437184; Hash = 'ca1e88e9a3c2a548fb34c3a621be5e6df671221e83bcbfb2a7942b3b73909706' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part10'; Length = 9437184; Hash = '6acef0c46ad153076d2245a9efcb9c40def2662e2092d7a22001a0015d8ed4a3' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part11'; Length = 9437184; Hash = '974e577eacdb9e1dbe5714855518f9fa7ba96b5af296ac66383b134046eab4ee' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part12'; Length = 9437184; Hash = '4e3ce015f72a0d5746908522fb804b14310492a236bce9cfa8d0a9c3a79a5a24' },
    @{ Name = 'FINAL_PACKED_PBR_v1.zip.part13'; Length = 5741361; Hash = 'ef00c899900b0e9e35a4758b57fed99e1d16625e480cf3206da770f1d657c3e1' }
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
