# Download only the v3 Unreal handoff

The repository is large; do not download its entire history or mix an old handoff with this one.

1. Save [Download_V3.ps1](Download_V3.ps1) using **Raw → Save As**, into `C:\Art`.
2. Open PowerShell in `C:\Art`, verify the helper and run it:

```powershell
$expected = '149591b4893bae02a1d8d8654ff9ed4ef6c626abb40218efd15b8faa5441f825'
if ((Get-FileHash .\Download_V3.ps1 -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'Downloader checksum mismatch' }
.\Download_V3.ps1
```

The helper downloads only this handoff, verifies every part and the reconstructed ZIP, and extracts into a new `C:\Art\EvergreenMarket_v3`. It refuses an existing extracted folder. Use `-Parent C:\Art\AnotherFreshFolder` to choose a different parent. If Windows blocks script execution, do not change a machine-wide policy; keep the exact error and ask for the smallest supported next step.

Then open `EvergreenMarket_v3/README.md` and run **preflight and sample only**. Full import requires the later manual sample approval. Actual Windows/Unreal execution has not run in this cloud workspace.
