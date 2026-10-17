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
$archive = 'FINAL_EXPORT_DELIVERY_v1.zip'
$expected = '5d724a73a2b1b6940d3cd73f659b77b3142fa3bbc2988247ea4252139e0f7c65'
$expectedLength = 262891346
$parts = @(
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part01'; Length = 9437184; Hash = '459dc30f7e4a1987952bbbdc9bfb2a380c5ca6a8bd038c10846aba5a332c1672' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part02'; Length = 9437184; Hash = 'e3e03c86b7f7473da6839f98112389337d1cc794c4ba093c4e222e0d6a7e60a3' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part03'; Length = 9437184; Hash = 'c24ce7003bf99e96432fe2a2d8c86ac6b9888a3137a655b2a36ad35ecdf40d4b' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part04'; Length = 9437184; Hash = '1788852d90b52c6a94335755e684818c76e666904cd040f5fb756cafd38651be' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part05'; Length = 9437184; Hash = 'e15f311f604186b8b3eab863d7d2594adde96d0df979e8f5ad65a7e45d61f854' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part06'; Length = 9437184; Hash = 'ff2609b946375d6a01a1aa4476c88e4fdac3ad19bbb9ff644771d3cadb35d8a0' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part07'; Length = 9437184; Hash = '5b5f6959340014ef70635cde02e1d088521c5706c514cb175d992128475bb44a' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part08'; Length = 9437184; Hash = 'bc5925f2e1f54b4bfdeecde5431ea1786598ac3ea40a6c896220f52e5fdb3e47' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part09'; Length = 9437184; Hash = '10cefafb63624df47ac9ba831a3ffca47e22d6315e573f5973eabbf84442fb9f' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part10'; Length = 9437184; Hash = 'd8f23ddc9d770ad068d687270f6ae36bd957fed553e3304287eaececc5816408' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part11'; Length = 9437184; Hash = '40508165192c29c0eeab052c0a6702869d4e1c144d195c68d82daf361c8cecde' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part12'; Length = 9437184; Hash = 'a64a4d1c16da86435599d3de4b6895e9875847cf4e2cdaca17234dfcf221a7ac' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part13'; Length = 9437184; Hash = 'a517cee077ec81f23293fcb2eb9ce60df4b92ec2b22a47520de8b53a78f1c763' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part14'; Length = 9437184; Hash = 'f171e503c61e1f186efbed03fbf3798459e0f9dd3efa72bf1d746c7b8bc10d31' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part15'; Length = 9437184; Hash = 'f532b1199151751052bc122108a56d90ea8bf2bfa181a76ce779cdaaf8f2443e' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part16'; Length = 9437184; Hash = 'b1d6c9ab98698999df3c9b1ab9f82095ecbbc3f03898664a4075b08aecc157f5' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part17'; Length = 9437184; Hash = 'f60313534572bf0c8c6b3efba3c78a0db5d3b4ce421aa95c9f4ea9172c29bbad' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part18'; Length = 9437184; Hash = 'dc7824e41161ca5b943c33bf05ee2b01f32daf43c61d8a3bcc0ddde2108e2f51' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part19'; Length = 9437184; Hash = 'f8f6ae399cfed3b35698464f3f1b9b2757fa0f9bcdabcf646797858db9b7cbce' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part20'; Length = 9437184; Hash = '1a23d7daf4c0cab81447305371260ea6b046188853032765efcc0360a3aec76e' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part21'; Length = 9437184; Hash = '77033b4ff1c6372fd08d3b4694acd1e97695b802a18fe6379c45a338755854a3' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part22'; Length = 9437184; Hash = '85940e08e5583b6f542965e52a1bf0cb937113c48f7b5838aa631f491113c842' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part23'; Length = 9437184; Hash = '8fce34f5c577b95e885087d3bba83b52aa1b48cb115d43a7090c7aaa80ac9466' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part24'; Length = 9437184; Hash = '386ae1386f30725289f8535cc25303b93ac217afb6f8603169ed817ec35e04e4' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part25'; Length = 9437184; Hash = 'deff26aec6e2f4075ab7278d230fa976e6bee0911ae440f2b70facd0ddcafe04' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part26'; Length = 9437184; Hash = '008fc2a8fcdbdff52d6aaa1b6f844f1de444ac0ebfb64dc172a08ca1ca09cf1c' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part27'; Length = 9437184; Hash = 'a65c5a4e399e693916e674bcb3f726bae6d4e3145ad24b70f323c58bd8ccb723' },
    @{ Name = 'FINAL_EXPORT_DELIVERY_v1.zip.part28'; Length = 8087378; Hash = '9f0d330bc37095847e8da5c576f2b6dbf68cf6103e437939f6ccb2eabc7f7c42' }
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
