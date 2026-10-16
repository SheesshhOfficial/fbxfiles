# Evergreen Market

## Download and open
Download the repository ZIP (Code → Download ZIP), or clone this repository. All project files are under **EvergreenMarket/**.

- **Original Blender scene:** `blender/Evergreen_Market.blend`. The complete original Blender package is `packages/Evergreen_Market_Blender_Package.zip`.
- **Reusable Unreal handoff:** In `packages/unreal_handoff/`, keep all five `.part01`–`.part05` files together and run `python Reassemble_Evergreen.py` (Windows: `py Reassemble_Evergreen.py`). The helper checks every part, the reconstructed ZIP SHA-256, and all ZIP CRCs. Extract the resulting `Evergreen_Market_Unreal_Handoff.zip`.
- **Converted native Blender scene:** The handoff ZIP contains `Evergreen_Market_Unreal_Ready.blend`, all 256 FBX assets, textures, placement/material manifests, scripts, and QA records.
- **Previews:** `previews/` and its view index. Some views are explicitly quick review renders.
- **Prop catalog/import instructions:** `docs/PROP_CATALOG.md`, `docs/PROP_ASSET_LIST.csv`, and `docs/UNREAL_IMPORT_AND_PROP_HUNT.md`.
- **Build/conversion source:** `source/blender/` and `source/unreal/`. These copies are for browsing; use the original package layouts for reproduction and review script paths before running.

## Scope and validation
256 unique mesh assets, 11,316 placements, 51 candidate prop variants and 6,695 candidate prop placements. Blender reopen and FBX roundtrip checks passed for all 256 assets. Local importer contract/data tests passed.

**Unreal Engine was not run.** This is an asset/import handoff, not a tested Unreal project. E-to-transform gameplay integration, collision tuning, navigation, lighting, performance and multiplayer remain to be implemented/tested in your game. See `docs/VALIDATION_SUMMARY.txt` for measured results and limitations.

The handoff ZIP SHA-256 is `b87f88a38882e763d2f2a6a21957734f1eb037187bfaa6a3ae81d4000cc6149e`. Repository file sizes, SHA-256s and Git blob IDs are in `FILE_MANIFEST.json`. The multipart format keeps individual uploads small without discarding any handoff files.
