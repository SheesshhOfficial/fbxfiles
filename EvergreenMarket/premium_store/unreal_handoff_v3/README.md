# Evergreen Market: matching v3 Unreal handoff

This package reconstructs the approved refined Blender v3 store in a **new Unreal 5.8 map**, using individual StaticMeshActors. The first run is a bounded calibration sample. **Do not run the full-map step until the sample passes.**

**Unreal has not been executed in this workspace.** Offline tests, source comparison, texture checks and Blender FBX roundtrips are recorded separately in `FINAL_QA_SUMMARY.json`. Gameplay, shader compilation, collision cooking, lighting, multiplayer and performance still require your actual project.

## Start here

1. Download only this package using the repository folder's [download guide](https://github.com/SheesshhOfficial/fbxfiles/blob/main/EvergreenMarket/premium_store/unreal_handoff_v3/DOWNLOAD.md). The helper verifies every part and the ZIP and extracts into a **fresh `C:\Art\EvergreenMarket_v3`**. Do not merge an old handoff into this folder.
2. Open `G:\Games\SheeshhPropHuntYT` in Unreal Editor **5.8.x**, save your current work, and ensure the Python editor scripting plugins are enabled.
3. Follow [the sample-first importer guide](importer/README.md). Its first steps inspect the package and create only `/Game/PremiumStoreV3/Sample_v001/Maps/L_V3_CalibrationSample` in a fresh version folder.
4. Check the axis probe, sample materials, selection, collision and containment. Restart the editor and verify saved assets. Only then explicitly approve and run the separate full-map command.

Existing assets, maps, Blueprints, GameMode, startup map and project settings are not overwritten. A failed run leaves its new partial version folder for inspection; it is never silently deleted or reused.

## What matches v3

- **6,593 source placements**, each an individual StaticMeshActor. **5,574 eligible copies** receive the Actor tag `Prop`; no ISM/HISM substitution.
- **264 canonical FBXs** with **235 canonical UCX hull objects**. The source's 231 collision-library hulls remain geometrically intact; four additional canonical copies support refined tree variants with the same authored world collision.
- Actual placed floor/wall materials, mounted v3 signage, refined v2 trees/facade, original counters and all other visible source geometry are reconciled. Old library materials are not substituted for edited instances.
- Portable baked PBR plus retained source images, explicit per-texture UV channels and a guarded material helper. Glass and fixture-emission policies are declared real-time approximations.
- **67 fixture lights**, ten actual PlayerStarts, four boundary metadata TargetPoints and four functional invisible perimeter barriers. No render-only sun/directional light is spawned. Light intensities are explicit provisional values, not a guaranteed Blender photometric match.
- Perimeter barriers follow the authored 64 m × 56 m footprint and 4.7 m height, with Pawn Block and Visibility Ignore. They do not replace the source physical walls or cover interior routes. Runtime containment remains a required sample test.

The full generated map has **6,678 role actors**: 6,593 source mesh actors, four invisible barrier actors, ten PlayerStarts, four boundary metadata markers and 67 lights. Only the 5,574 eligible source actors are tagged `Prop`.

## Existing prop-hunt interaction

`BP_propChar` is unchanged. Its server-side single Visibility sphere trace can hit a floor, wall or another blocker before the desired prop. **Individual actors and Prop tags do not establish trace reachability.** The sample checklist requires near-floor/occluded/large-prop selection, disguise collision/capsule clearance and the two-client multicast path. Do not approve full import just because the map renders.

## Source and contents

The approved Blender source is unchanged: `YOU_WANT_IT_YOU_GET_IT_REFINED_v3.blend`, SHA-256 `c4abf30a478051c30e00536642416c53fefb7db4911128dbb8114c0732975519`. It remains in the [separate published source package](https://github.com/SheesshhOfficial/fbxfiles/tree/4d69de9f8fad9823208b6836023a0e792db88069/EvergreenMarket/premium_store/refinement_v3). This handoff contains the matching export and importer, not another editable-source copy.

- `export/`: canonical FBXs, texture payloads, placement/material/UV contracts, scene support and roundtrip evidence
- `qa_axis/`: regenerated asymmetric calibration probe
- `importer/`: dry-run/apply code, tests, false-initialized sample checklist and full instructions
- `independent_qa/`: independent source, material, geometry, transform, boundary and integration evidence
- `tools/`: reproducible Blender preparation/bake/export/validation tooling
- `FILE_INVENTORY.json`: every packaged file's size and SHA-256
- `SOURCE_PROVENANCE.json` and `FINAL_QA_SUMMARY.json`: exact source lineage and tested/untested status

The original Blender source is never saved by this pipeline. Text conversion, exact-zero text-face cleanup, UV preparation and baking take place in separate derivatives. The earlier exterior face-material preparation defect was caught by independent QA, fixed and regenerated before delivery; rejected intermediate outputs are not runtime inputs.
