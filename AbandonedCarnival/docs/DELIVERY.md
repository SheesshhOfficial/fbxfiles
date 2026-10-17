# Refined carnival delivery

## Editable source
This package contains one final source split into 15 binary parts under `blender/`. Run `source/Reassemble_Blender_Windows.cmd` from the complete folder, then open `blender/Moonfall_Carnival_Refined.blend`. Built-in PowerShell validates part lengths and SHA256 before assembly and checks the final file. No Python installation, administrator access, or execution-policy change is required. A differing existing output is not overwritten. The native-chat tools ZIP uses its own flat download layout; follow its included README instead.

Final file: 136,393,382 bytes. SHA256: `2d4f00dbf3704895a79ea30287dfa93ac7d0ad87f6e03e0e1ea163888418ca1a`. Blender 4.3.2 source, 41 packed images. All ten sequential checkpoints remain preserved locally; only the final source is included here to avoid duplicate large downloads.

## Current engine assets
`export/unreal/` contains current V2 FBXs, placement/material/light metadata and guarded import helpers. `export/textures/` holds referenced textures. Read `FINAL_QA_SUMMARY.md`, `COLLISION_BUDGET.md`, and `UNREAL_ACCEPTANCE_CHECKLIST.md` first. This folder is matched to the final source hash; do not combine it with V1 FBXs. The importer targets `/Game/MoonfallCarnivalV2/`. Blueprint behavior is unchanged. Unreal import/collision cooking/playability/performance are not verified.

## Preview and provenance
`renders/` contains actual Blender cycle evidence, including cleaner final maintenance and ticket views. Grain and remaining stylization are visible; these are authored realism-targeted art assets, not a photographic-perfection claim. The ten-pass change log is in `TEN_PASS_CHANGELOG.md`. Licenses and source provenance are included.

## Delivery state
The source parts and updated reconstruction tools were sent through native chat. The complete local package is staged for the requested AbandonedCarnival repository folder. Publication status must be checked separately; local staging does not establish a remote commit.
