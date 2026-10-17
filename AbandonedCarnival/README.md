# Moonfall Carnival — ten-pass refined source

Abandoned nighttime carnival PropHunt environment. Ten sequential geometry, materials, dressing and lighting refinement cycles are preserved locally and summarized in docs/TEN_PASS_CHANGELOG.md. This is a realism-targeted editable art build, not a claim of photographic perfection or verified Unreal gameplay.

## Open the Blender source on Windows

1. Download this complete AbandonedCarnival folder with all 15 source parts.
2. Double-click source/Reassemble_Blender_Windows.cmd. It uses built-in PowerShell, requires no Python/admin/execution-policy change, and validates every part and the final SHA256.
3. Open blender/Moonfall_Carnival_Refined.blend in Blender 4.3.2 or a compatible newer version. All 41 images are packed.

The standalone native-chat source download uses the separate Carnival_Source_Tools.zip launcher and the same part bytes. Follow the README inside that tools ZIP for its flat download layout.

## Current scope

- Six connected zones: midway stalls, bumper arena, carousel, funhouse, backstage trailers and ticket entrance
- 153 separate eligible prop placements; 10 player starts
- About 3.54 million visible evaluated mesh triangles; performance needs target-engine profiling
- Source UV/material/finite-geometry/zero-area checks passed; three pre-existing visual meshes retain open decorative tube ends on retired seats/generator, as documented
- No interaction Blueprint modifications

## Matched engine package

The current export folder is generated only from the frozen Cycle 10 source. Read docs/FINAL_QA_SUMMARY.md and docs/UNREAL_ACCEPTANCE_CHECKLIST.md before importing. Use a fresh V2 content namespace/level. Never mix the earlier V1 FBXs with this refined source.

Unreal import, collision cooking, navigation, lighting/material fidelity, multiplayer interaction and performance are untested. Imported source normals and generated tangents must be visually checked. The existing single-hit Visibility sphere trace can hit scenery first and then reject it; preserve the Blueprint behavior and test each placement.

## Reproducibility

Authoring modules are under source and sequential refinement runners under iterations/source. For a fresh export, copy the reconstructed source to iterations/Cycle_10.blend and follow iterations/source/EXPORT_V2.md and EXPORT_PROPS_V2.md using the frozen hash in qa/Frozen_Source.json. Do not run historical build scripts against a valued edited scene: several intentionally create or save earlier source paths. Keep a backup.

Licenses/provenance: docs/ASSET_PROVENANCE.md, source/realistic_asset_sources.json and docs/DejaVu_Font_License.txt. No paid or ripped models are included.
