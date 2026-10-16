# Evergreen Market

## New premium store: layout approval stage

[View the proposed floor plan, Blender blockout previews and design ZIP](premium_store/design_v1/). This new 64 × 56 m single-floor Evergreen concept includes premium departments and connected stock/staff routes. These are layout blockouts, not finished artwork or a gameplay-ready import. Every eventual eligible placement must be individually transformable; detailed production awaits layout approval. Existing delivery versions below remain untouched.

## Controlled expansion: 16 original props

Use the small [prop-batch ZIP](packages/prop_batch/Evergreen_Prop_Batch.zip) and [two-command guide](docs/PROP_BATCH.md) on the successful fixture-lit v2 map. It creates a separate short-named map with 16 additional original-position cans, bottles, cartons and boxes, preserving the four existing props, the user-approved 31 remaining lights and 694 walking colliders. Dry-run first. Offline tests passed; actual E interaction and multiplayer still need playtesting.

## Fixture-aligned lighting for a working v2 map

Use the small [fixture-lighting ZIP](packages/fixture_lighting/Evergreen_Fixture_Lighting.zip) and [two-command guide](docs/FIXTURE_LIGHTS.md) to create a lighting-only map copy with 42 actual fixture points: 25 ceiling/warehouse, 15 canopy and 2 wall lamps. It replaces only the 11 generated preview lights, including the generated Sun, and preserves geometry, 694 colliders, four working props, PlayerStart and unrelated manual lights. No asset reimport or full-package download is needed. Settings are an initial visual/performance test, not a promise of calibrated brightness or frame rate.

## Latest complete Blender-source v2 package

Use [packages/source_v2](packages/source_v2) for the corrected native Blender master, all 256 render FBXs, 86 collision companions, textures, source-defined lighting and fresh-import helpers. The [v2 guide](docs/FRESH_SOURCE_V2.md) creates new maps with 694 reviewed walking boxes, four E-compatible pilot actors and 11 neutral preview lights. No previous package, patch or reports are needed. Keep your working map.

Double-click `Reassemble_Source_v2_Windows.cmd` beside all archive parts, then extract the verified ZIP to `C:\Art`. Read the included `START_HERE.md`. The 51 prop-candidate FBXs contain their own UBX hulls; render-only fixtures require their separate companion policy via the importer. Character movement/capsule behavior still belongs to the game Blueprint. Local geometry/export/tests pass; the new workflow still needs Unreal runtime acceptance. Older packages and repair routes below remain for existing runs; do not mix their helper files with v2.

If fresh sample lighting stopped with `Preview transform changed` and the Sun has scale 2.5, use the [scoped Sun-scale recovery](docs/LIGHTING_RECOVERY.md). It retains the sample and repairs the existing light without reimporting meshes.

## Fresh start with all corrected meshes

For a new level, use the [fresh-start guide](docs/FRESH_START.md) and consolidated helpers in `packages/fresh_start/`. This prepares a separate corrected package before importing all 256 assets (178 corrected FBXs), then builds walking collision and four E-compatible pilot props. It does not depend on old maps/reports. Optional preview lighting and PlayerStart are provided; gameplay and visual checks remain required.

For four working E props whose report failed with `Pilot collision mismatch`, use the [four-prop collision-profile repair](docs/PILOT_COLLISION_REPAIR.md) before the normals patch. It copies the current map and verifies persistence.

## Geometry correction: inward cube faces

The original handoff contains inward-wound box geometry. Use the versioned [normals repair guide](docs/NORMALS_REPAIR.md) and patch in `packages/normals_patch/` rather than enabling Two Sided globally or reimporting the complete scene. The patch preserves original maps/assets and creates a corrected copy, with a box/checkout sample before the full affected set. Existing original archives are retained for reproducibility and have not silently changed. The source box and UBX generators below now use outward winding.

## Importer update required

After extracting the handoff ZIP, copy the current `source/unreal/import_supermarket_unreal.py` from this repository over the extracted package's `source/import_supermarket_unreal.py`. The archive retains its original version. This fixes the collision-enum error during sample assembly; see [hotfix and retry steps](docs/IMPORTER_HOTFIX.md).

## Walking collision after the full import

If the character falls through the map, use the [walk-test collision helper and finishing checklist](docs/WALK_COLLISION_AND_FINISHING.md). It adds reviewed floor/wall/fixture collision to a new map copy without reimporting assets. Dry run first; the new helper still needs an actual Unreal walk test.

## Existing StaticMeshActor-based prop gameplay

For a ChangeProp Blueprint that casts HitActor to StaticMeshActor, try the [four-prop compatibility pilot](docs/PROP_ACTOR_COMPATIBILITY_PILOT.md) after the walking collision step. It converts only four selected props in another map copy; the guide explains the separate floor-first Visibility trace risk.

## Download and open
Download the repository ZIP (Code → Download ZIP), or clone this repository. All project files are under **EvergreenMarket/**.

- **Original Blender scene:** `blender/Evergreen_Market.blend`. The complete original Blender package is `packages/Evergreen_Market_Blender_Package.zip`.
- **Reusable Unreal handoff:** In `packages/unreal_handoff/`, keep all five `.part01`–`.part05` files together. **On Windows, double-click `Reassemble_Evergreen_Windows.cmd` in that same folder. No Python or installation is needed.** It uses built-in Windows PowerShell, checks every part's size/SHA-256 and the final ZIP size/SHA-256, and pauses so errors stay visible. It never replaces an existing ZIP and changes no execution-policy settings. The Windows launcher was statically reviewed but could not be executed on Windows in the build environment. Alternatively, run `python Reassemble_Evergreen.py` (or `py Reassemble_Evergreen.py` if Python is installed); that helper additionally checks ZIP CRCs. Extract the resulting `Evergreen_Market_Unreal_Handoff.zip`.
- **Converted native Blender scene:** The handoff ZIP contains `Evergreen_Market_Unreal_Ready.blend`, all 256 FBX assets, textures, placement/material manifests, scripts, and QA records.
- **Previews:** `previews/` and its view index. Some views are explicitly quick review renders.
- **Prop catalog/import instructions:** `docs/PROP_CATALOG.md`, `docs/PROP_ASSET_LIST.csv`, and `docs/UNREAL_IMPORT_AND_PROP_HUNT.md`.
- **Build/conversion source:** `source/blender/` and `source/unreal/`. These copies are for browsing; use the original package layouts for reproduction and review script paths before running.

## Scope and validation
256 unique mesh assets, 11,316 placements, 51 candidate prop variants and 6,695 candidate prop placements. Blender reopen and FBX roundtrip checks passed for all 256 assets. Local importer contract/data tests passed.

**Unreal Engine was not run.** This is an asset/import handoff, not a tested Unreal project. E-to-transform gameplay integration, collision tuning, navigation, lighting, performance and multiplayer remain to be implemented/tested in your game. See `docs/VALIDATION_SUMMARY.txt` for measured results and limitations.

The handoff ZIP SHA-256 is `b87f88a38882e763d2f2a6a21957734f1eb037187bfaa6a3ae81d4000cc6149e`. Repository file sizes, SHA-256s and Git blob IDs are in `FILE_MANIFEST.json`. The multipart format keeps individual uploads small without discarding any handoff files.
