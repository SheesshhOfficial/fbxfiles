# Complete Blender-source v2 package

Keep all six `.part01`–`.part06` files beside `Reassemble_Source_v2_Windows.cmd`. On Windows, double-click the CMD file, then extract the verified ZIP into `C:\Art`.

The folder becomes `C:\Art\Evergreen_Market_Source_v2`. Read `START_HERE.md`, then `source/unreal/FRESH_SOURCE_V2.md`. Keep your working map. Use the new v2 helpers only; no original package or normals patch is needed.

The Windows launcher uses built-in PowerShell 5.1, verifies every part and complete archive, preserves an existing output, pauses on errors, and changes no execution policy. Windows execution was unavailable here; the launcher was statically checked. The Python alternative `Reassemble_Source_v2.py` was executed successfully, including final SHA256 and ZIP CRC validation.

Package: native corrected `.blend`, 256 render FBXs, 86 collision companion FBXs, textures, placement/material manifests, source-defined collision and light layout, fresh importer, source scripts and QA. New workflow: 694 walking boxes, four individually tagged prop actors, 11 neutral lights. Character Blueprint behavior is unchanged. Unreal runtime acceptance remains required.

See `archive_manifest.json` and `SHA256SUMS.txt` for exact sizes/hashes. The assembled archive is 53,216,166 bytes. Its SHA256 is `21c85917a12ca5709215783ed4e02522ad942c652ac76927525e030c920cdbab`.
