param([string]$Parent = 'C:\Art', [string]$Revision = 'main')
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
# Public repository. Exact payload hashes below fail closed if remote bytes change.
$spec = @'
{
  "archive": "EvergreenMarket_v3_Unreal_Handoff.zip",
  "bytes": 380086638,
  "sha256": "8046567922712d81f89f6418125bbc02defd9bd7b6e05e88aa9a6d1bc7baf32f",
  "parts": [
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part01",
      "bytes": 9437184,
      "sha256": "1af9d481e2162a8d938a7373f972fe3d8794d46f173b771c714a9b43c048efd2"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part02",
      "bytes": 9437184,
      "sha256": "195f664ab562bec473bb09f17657e544ae90f7ac6b403a99147739c955e2df8c"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part03",
      "bytes": 9437184,
      "sha256": "ba09952fe85499c2deb0b849a197dd7048610c0d4ebe7e4612b451b1baf7b8f2"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part04",
      "bytes": 9437184,
      "sha256": "c524fce7640dcd1fa97a91d969d94d3322022c27f46e29d1ed57d34861eb0bc2"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part05",
      "bytes": 9437184,
      "sha256": "753fdb6370ced15e0a624c9fa964392e8305543290fa05255b71318f25f213d5"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part06",
      "bytes": 9437184,
      "sha256": "e4b4baead1ab4eb0b194fd77eb53af23813b79ecf562fbbbe7cd523062091865"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part07",
      "bytes": 9437184,
      "sha256": "29cfcc9a22ea49520bd517d35c4c270b49d34ac036bf8ca9bdbe821ab1680e55"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part08",
      "bytes": 9437184,
      "sha256": "60e0352f515658e77e7b1d0bda57a8ea3f318d6311e1e0eb99b1a0bbd669950e"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part09",
      "bytes": 9437184,
      "sha256": "ffc94de62a2c5ba134da7def61c184e1660e4384c44dbd64fad970f2f4a201db"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part10",
      "bytes": 9437184,
      "sha256": "87da2c1433d2e445e9163e7dfb6848fcea5a120f3bc08133f11bbcc0c55bc9f9"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part11",
      "bytes": 9437184,
      "sha256": "fb8514054cc15a82d7c0d2bb3434ea4a32a506ebda0ed672f3c701297b4321d3"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part12",
      "bytes": 9437184,
      "sha256": "331322f34b033bc80b0ea3bc51923e7a26ec15b440bf6c9e67bc991077be463e"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part13",
      "bytes": 9437184,
      "sha256": "7947f2ecd3c8c7175ea353b5ae89ac87ef847555d242cf515069a90248dc98bb"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part14",
      "bytes": 9437184,
      "sha256": "090763376b2458d97f579ecf02193adb4b50161f04e49a27c35086061c01f819"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part15",
      "bytes": 9437184,
      "sha256": "2bba93af351ce742a73476cfbde599660d3b05b5260fd7f347c6501b0dfe4ad1"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part16",
      "bytes": 9437184,
      "sha256": "540f40ea5568d5eaecfdaf0a7cc236e0e67f5842ef013d55d0e3ff49b811cbe8"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part17",
      "bytes": 9437184,
      "sha256": "857d3cbf4312c4f6d8f5410476f56bf900d05de2647f5ec86be869d6920f3a6f"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part18",
      "bytes": 9437184,
      "sha256": "8149ae9312af49930b2938346f89b98b8ad237902ef43f21c8e1f5ae4d43b2da"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part19",
      "bytes": 9437184,
      "sha256": "adf37fec0619f62a9f3dcaef291e6338edbeb87f5659824db9090865ab343cfc"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part20",
      "bytes": 9437184,
      "sha256": "4b26dd1793ed59c96b60d4b53f17b1edaadb0189865c69b93f20a400eab6af04"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part21",
      "bytes": 9437184,
      "sha256": "de2cc9a1ca8b69ccb4f1972e7e6b8faeab2de34b7a2fb4ee1e065ed0b4a9d52c"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part22",
      "bytes": 9437184,
      "sha256": "a51c5623d51f78aa214ab06e3315eb5c04fd67b446993810420c7ac70f905c74"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part23",
      "bytes": 9437184,
      "sha256": "c84dbf254da1a238d6e8c97a17bf6d2072b67e59a992d6f447f4d343bf4aa328"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part24",
      "bytes": 9437184,
      "sha256": "ee16eba21ce54910763660094b9f83b98a1f40fc5531fd187d4f4b629186b972"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part25",
      "bytes": 9437184,
      "sha256": "b09d44bc5290c644c38412a2be4efe9e2c12a0c1867655eed8de79a2e0dd9d4c"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part26",
      "bytes": 9437184,
      "sha256": "84c0189e1ea66deb88b0a5259ff56df67f1c13e99c405bed60b05baafc82b34d"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part27",
      "bytes": 9437184,
      "sha256": "7ef3ed75940ef0e9b84516a945f464f2363e175d544bb17827c80507e28770d6"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part28",
      "bytes": 9437184,
      "sha256": "9c17d135c8f56207a1c3104fca708fed3ac22f1bde4e6280560c631e6c86a2a7"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part29",
      "bytes": 9437184,
      "sha256": "b70823ad08280aea506de1efff0a0ba4f787caabce752a299d660671c930b346"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part30",
      "bytes": 9437184,
      "sha256": "bc72e0bdabbdde59120cecccec3e068d70cb2238c1518a33c89f2cfb8a3f8d91"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part31",
      "bytes": 9437184,
      "sha256": "80f0d836fd752a91b9e93df38d69bb6f63fd04c8b8213e3cf74555351c8c7306"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part32",
      "bytes": 9437184,
      "sha256": "6a9318c7731e0934a4298e7d4bc01c69fff0f1630576491f902df6ec7cf6a9ad"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part33",
      "bytes": 9437184,
      "sha256": "10594487e10769c7f477bcdde5629a1dc44d2e80d535b492359a535dcb03b93f"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part34",
      "bytes": 9437184,
      "sha256": "1b261d1f0f1478ad6ebb045c4dd86c0c00fef5c86e96eb72bd9e450d9b245051"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part35",
      "bytes": 9437184,
      "sha256": "9eeea4f78a7b8665dce89b89768f524dc73efa5c0ecaaf118b05a8b197bb0eb1"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part36",
      "bytes": 9437184,
      "sha256": "c90bf26bb6bb42ba7fd21769c68e2a87f4c0fe3f342fd7849caad9523617eea6"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part37",
      "bytes": 9437184,
      "sha256": "dc5e7b19f5e2ff640c83c4a0318dd8ffb21989bec95d0980af81dd65b79424c6"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part38",
      "bytes": 9437184,
      "sha256": "c4b1888ab58ee395ecf14401d170386dd14450195ccfea28fab93b62ac77c554"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part39",
      "bytes": 9437184,
      "sha256": "2f2cc0ece3d9c74e0e108b82fa64c32150433b331c029e4ebe47e505b1a1fdaa"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part40",
      "bytes": 9437184,
      "sha256": "084cf841cdde3383c5cc7e81e1fe681ff6e2a8c8bb976f06110450c4c0789855"
    },
    {
      "name": "EvergreenMarket_v3_Unreal_Handoff.zip.part41",
      "bytes": 2599278,
      "sha256": "6d89a28f7036382ca76b7a0fe33b684d488d22a51bdcd4a53400a149ace419ba"
    }
  ]
}
'@ | ConvertFrom-Json
$destination = Join-Path $Parent 'EvergreenMarket_v3'
if (Test-Path -LiteralPath $destination) { throw "Destination already exists: $destination. Choose a fresh -Parent directory; nothing was overwritten." }
$download = Join-Path $Parent 'EvergreenMarket_v3_download'
New-Item -ItemType Directory -Force -Path $download | Out-Null
$base = "https://raw.githubusercontent.com/SheesshhOfficial/fbxfiles/$Revision/EvergreenMarket/premium_store/unreal_handoff_v3/download"
function Assert-File($path, $size, $hash) {
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing file: $path" }
  if ((Get-Item -LiteralPath $path).Length -ne $size) { throw "Wrong file size: $path" }
  if ((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() -ne $hash) { throw "Checksum mismatch: $path" }
}
foreach ($part in $spec.parts) {
  $file = Join-Path $download $part.name
  if (!(Test-Path -LiteralPath $file)) {
    $partial = "$file.partial"
    if (Test-Path -LiteralPath $partial) { throw "An incomplete download exists: $partial. Move it aside before retrying." }
    Write-Host "Downloading $($part.name)"
    Invoke-WebRequest -UseBasicParsing -Uri "$base/$($part.name)" -OutFile $partial
    Assert-File $partial $part.bytes $part.sha256
    Move-Item -LiteralPath $partial -Destination $file
  }
  Assert-File $file $part.bytes $part.sha256
}
$archive = Join-Path $download $spec.archive
if (!(Test-Path -LiteralPath $archive)) {
  $partial = "$archive.partial"
  $stream = [IO.File]::Open($partial, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
  try {
    foreach ($part in $spec.parts) {
      $inputStream = [IO.File]::OpenRead((Join-Path $download $part.name))
      try { $inputStream.CopyTo($stream) } finally { $inputStream.Dispose() }
    }
  } finally { $stream.Dispose() }
  Assert-File $partial $spec.bytes $spec.sha256
  Move-Item -LiteralPath $partial -Destination $archive
}
Assert-File $archive $spec.bytes $spec.sha256
Expand-Archive -LiteralPath $archive -DestinationPath $Parent
if (!(Test-Path -LiteralPath (Join-Path $destination 'README.md'))) { throw 'Extraction did not produce the expected handoff folder.' }
Write-Host "Verified and extracted: $destination"
Write-Host 'Open README.md. Run preflight and sample only; full import requires your sample acceptance.'
