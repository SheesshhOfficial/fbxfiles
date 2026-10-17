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
$archive = 'EvergreenMarket_v3_Unreal_Handoff.zip'
$expected = '8046567922712d81f89f6418125bbc02defd9bd7b6e05e88aa9a6d1bc7baf32f'
$expectedLength = 380086638
$parts = @(
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part01'; Length = 9437184; Hash = '1af9d481e2162a8d938a7373f972fe3d8794d46f173b771c714a9b43c048efd2' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part02'; Length = 9437184; Hash = '195f664ab562bec473bb09f17657e544ae90f7ac6b403a99147739c955e2df8c' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part03'; Length = 9437184; Hash = 'ba09952fe85499c2deb0b849a197dd7048610c0d4ebe7e4612b451b1baf7b8f2' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part04'; Length = 9437184; Hash = 'c524fce7640dcd1fa97a91d969d94d3322022c27f46e29d1ed57d34861eb0bc2' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part05'; Length = 9437184; Hash = '753fdb6370ced15e0a624c9fa964392e8305543290fa05255b71318f25f213d5' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part06'; Length = 9437184; Hash = 'e4b4baead1ab4eb0b194fd77eb53af23813b79ecf562fbbbe7cd523062091865' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part07'; Length = 9437184; Hash = '29cfcc9a22ea49520bd517d35c4c270b49d34ac036bf8ca9bdbe821ab1680e55' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part08'; Length = 9437184; Hash = '60e0352f515658e77e7b1d0bda57a8ea3f318d6311e1e0eb99b1a0bbd669950e' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part09'; Length = 9437184; Hash = 'ffc94de62a2c5ba134da7def61c184e1660e4384c44dbd64fad970f2f4a201db' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part10'; Length = 9437184; Hash = '87da2c1433d2e445e9163e7dfb6848fcea5a120f3bc08133f11bbcc0c55bc9f9' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part11'; Length = 9437184; Hash = 'fb8514054cc15a82d7c0d2bb3434ea4a32a506ebda0ed672f3c701297b4321d3' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part12'; Length = 9437184; Hash = '331322f34b033bc80b0ea3bc51923e7a26ec15b440bf6c9e67bc991077be463e' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part13'; Length = 9437184; Hash = '7947f2ecd3c8c7175ea353b5ae89ac87ef847555d242cf515069a90248dc98bb' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part14'; Length = 9437184; Hash = '090763376b2458d97f579ecf02193adb4b50161f04e49a27c35086061c01f819' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part15'; Length = 9437184; Hash = '2bba93af351ce742a73476cfbde599660d3b05b5260fd7f347c6501b0dfe4ad1' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part16'; Length = 9437184; Hash = '540f40ea5568d5eaecfdaf0a7cc236e0e67f5842ef013d55d0e3ff49b811cbe8' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part17'; Length = 9437184; Hash = '857d3cbf4312c4f6d8f5410476f56bf900d05de2647f5ec86be869d6920f3a6f' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part18'; Length = 9437184; Hash = '8149ae9312af49930b2938346f89b98b8ad237902ef43f21c8e1f5ae4d43b2da' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part19'; Length = 9437184; Hash = 'adf37fec0619f62a9f3dcaef291e6338edbeb87f5659824db9090865ab343cfc' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part20'; Length = 9437184; Hash = '4b26dd1793ed59c96b60d4b53f17b1edaadb0189865c69b93f20a400eab6af04' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part21'; Length = 9437184; Hash = 'de2cc9a1ca8b69ccb4f1972e7e6b8faeab2de34b7a2fb4ee1e065ed0b4a9d52c' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part22'; Length = 9437184; Hash = 'a51c5623d51f78aa214ab06e3315eb5c04fd67b446993810420c7ac70f905c74' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part23'; Length = 9437184; Hash = 'c84dbf254da1a238d6e8c97a17bf6d2072b67e59a992d6f447f4d343bf4aa328' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part24'; Length = 9437184; Hash = 'ee16eba21ce54910763660094b9f83b98a1f40fc5531fd187d4f4b629186b972' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part25'; Length = 9437184; Hash = 'b09d44bc5290c644c38412a2be4efe9e2c12a0c1867655eed8de79a2e0dd9d4c' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part26'; Length = 9437184; Hash = '84c0189e1ea66deb88b0a5259ff56df67f1c13e99c405bed60b05baafc82b34d' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part27'; Length = 9437184; Hash = '7ef3ed75940ef0e9b84516a945f464f2363e175d544bb17827c80507e28770d6' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part28'; Length = 9437184; Hash = '9c17d135c8f56207a1c3104fca708fed3ac22f1bde4e6280560c631e6c86a2a7' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part29'; Length = 9437184; Hash = 'b70823ad08280aea506de1efff0a0ba4f787caabce752a299d660671c930b346' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part30'; Length = 9437184; Hash = 'bc72e0bdabbdde59120cecccec3e068d70cb2238c1518a33c89f2cfb8a3f8d91' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part31'; Length = 9437184; Hash = '80f0d836fd752a91b9e93df38d69bb6f63fd04c8b8213e3cf74555351c8c7306' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part32'; Length = 9437184; Hash = '6a9318c7731e0934a4298e7d4bc01c69fff0f1630576491f902df6ec7cf6a9ad' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part33'; Length = 9437184; Hash = '10594487e10769c7f477bcdde5629a1dc44d2e80d535b492359a535dcb03b93f' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part34'; Length = 9437184; Hash = '1b261d1f0f1478ad6ebb045c4dd86c0c00fef5c86e96eb72bd9e450d9b245051' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part35'; Length = 9437184; Hash = '9eeea4f78a7b8665dce89b89768f524dc73efa5c0ecaaf118b05a8b197bb0eb1' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part36'; Length = 9437184; Hash = 'c90bf26bb6bb42ba7fd21769c68e2a87f4c0fe3f342fd7849caad9523617eea6' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part37'; Length = 9437184; Hash = 'dc5e7b19f5e2ff640c83c4a0318dd8ffb21989bec95d0980af81dd65b79424c6' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part38'; Length = 9437184; Hash = 'c4b1888ab58ee395ecf14401d170386dd14450195ccfea28fab93b62ac77c554' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part39'; Length = 9437184; Hash = '2f2cc0ece3d9c74e0e108b82fa64c32150433b331c029e4ebe47e505b1a1fdaa' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part40'; Length = 9437184; Hash = '084cf841cdde3383c5cc7e81e1fe681ff6e2a8c8bb976f06110450c4c0789855' },
    @{ Name = 'EvergreenMarket_v3_Unreal_Handoff.zip.part41'; Length = 2599278; Hash = '6d89a28f7036382ca76b7a0fe33b684d488d22a51bdcd4a53400a149ace419ba' }
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
