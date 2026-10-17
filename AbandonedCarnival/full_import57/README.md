# Full carnival import for Unreal Engine 5.7.4

This additive importer creates a new, unsaved world and `/Game/AbandonedCarnivalFull57`. It uses the frozen AbandonedCarnival export and the unchanged geometry/material helper code that passed the smaller UE 5.7.4 calibration. The full scene has not yet passed an Unreal runtime or visual review.

## Exact scope

- 138 canonical prop meshes, placed as 153 separate native StaticMeshActors with their source PropActor tags.
- 43 environment meshes/actors. Eight intentionally have no collision.
- 59 materials, including one documented translucent glass approximation; 41 texture/usage assets.
- 10 native PlayerStarts and 41 source lights: 33 PointLights, 7 RectLights, 1 DirectionalLight.
- Total: 281 content assets and 247 authored actors, plus Unreal's world infrastructure.
- No Blueprints, current-map editing, existing-asset replacement, save, delete, cleanup, automatic retry, or renderer/exposure setting changes. The saved calibration content stays separate.

All used FBX, texture and metadata files are checked against the pinned original FILE_MANIFEST. The original source's 15 parts are verified by their hashes and their combined source hash. JSON/Python pins permit only CRLF-to-LF normalization; binary hashes remain exact. Additional importer files do not require changing the frozen FILE_MANIFEST.

## Before running

1. Pull the approved `full_import57` folder into your existing package root. Keep all nine delivered files together; no dependency installation is required.
2. Use Unreal **5.7.4**, with the same Editor Python setup used for calibration. Stop Play/Simulate.
3. Manually save any wanted calibration assets and map, or discard unwanted edits yourself. Preflight blocks any dirty map or content package.
4. `/Game/AbandonedCarnivalFull57` and its physical Content folder must not exist. A partial prior attempt is deliberately blocked. Inspect it before deciding manually what to retain/discard.
5. Source RectLights require deferred rendering. Forward rendering is blocked; this helper never changes it. Close other heavy applications if memory is tight. The full import is much larger than calibration.

## Read-only preflight

Run this in the Unreal Python console (one line). It does not create assets, actors, maps, or report files:

```python
import sys, json; sys.dont_write_bytecode = True; root = r"G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival"; sys.path.insert(0, root + r"\full_import57"); import carnival_full_import57 as f; full_preflight = f.preflight(root); print(json.dumps({k: full_preflight.get(k) for k in ("status", "engine_version", "verified_file_count", "errors")}, indent=2))
```

Expected inside Unreal: `FULL_PREFLIGHT_PASS`. Outside Unreal, `FILES_VERIFIED_ENGINE_NOT_CHECKED` verifies source files only. A successful preflight does not authorize a cached bypass: import repeats all checks.

## Explicit full import

After reviewing preflight, this is the single mutating entry point:

```python
full_report = f.import_full(root); print(json.dumps({k: full_report.get(k) for k in ("status", "world_path", "counts", "validation", "errors")}, indent=2))
```

The importer creates a **fresh blank unsaved map**, then processes one texture or FBX import task at a time. The Output Log reports each texture/material/mesh/actor count. A zero-hull environment tile is tested first in the mesh stage because that BodySetup case is new to the full scene. Actual returned asset paths, legacy importer provenance, source filenames, texture settings, ordered slots, UV counts, centimetre bounds and exact UCX counts are checked. No auto-generated or complex-as-simple replacement collision is used. All solid actors block Pawn and Visibility; zero-hull decoration has collision disabled. These are structural settings, not a gameplay test.

Success is `FULL_IMPORT_CREATED_UNSAVED`. Wait for Unreal's background compilation, inspect the log and scene, then manually Save As:

`/Game/AbandonedCarnivalFull57/Maps/AbandonedCarnivalFull57`

Save wanted content manually. The helper performs zero saves; Unreal's independent autosave is unchanged and may still occur.

Failure raises `FullImportError` with a structured `.report` and prints that report in the exception. It lists attempted/created assets and actors, current namespace contents, failure stage and partial-import status. Partial content is left for inspection. Do not rerun over it. No existing map or asset assignments need rollback because all mutations target newly created full-import content.

## Read-only check after import or manual save

With the full map open:

```python
full_audit = f.validate(root); print(json.dumps(full_audit, indent=2))
```

Dirty packages are allowed and listed. This validates the existing inventory, source provenance/settings, mesh/material assignments, actor transforms/tags, collision settings, light properties and source forward/up vectors. It does not re-traverse material graphs or establish shader compilation, visual quality, light matching, player clearance, multiplayer behavior or performance. `visual_pass` remains false until a separate human review; `FULL_STRUCTURE_PASS` is structural only.

## Material, light and performance limits

- The one `glass` material uses Default Lit translucent, Surface Per Pixel Lighting and index-of-refraction settings. Source opacity/IOR are approximations, not a physically matched Blender shader. Names containing “glass” do not determine blend mode. Source tints and two-sided foliage settings are preserved. One prepared material, “Moon surface,” is intentionally unused.
- Source light positions, directions, colors and shadow flags are preserved. All 41 lights cast shadows and are movable. Brightness is approximate: 100 lumens per source local-light watt and 1 lux per source directional unit.
- Local attenuation is an explicit **source-ground Z=0 heuristic**: max(1,200 cm, 2 × area width, 2 × positive light height). Its computed radius is recorded per light and checked again. It is not source photometric equivalence.
- All seven source disk area lights become square RectLights of equal source width/height. Orientation is checked with forward/up vectors, including pitch -90°. A transient nonwhite color roundtrip must pass before any persistent mutation; no alternative color flag is silently tried.
- Texture and FBX tasks are submitted sequentially, but Unreal may compile textures/shaders asynchronously. Sequential submission is not a peak-memory bound or compilation-complete guarantee. Texture base-level RGBA equivalents alone total about 408.75 MiB before mips, mesh buffers, derived data or compiler overhead.
- No sky, reflection capture, fog, ground support or exposure is added. Source Blender world/render-only effects are excluded. Use viewport inspection and chosen exposure for review; no lighting or gameplay match is claimed.
- Raw FBX/source fidelity passed. Known Blender reimport normal caveats remain: 24 environment tiles contain 4,795 corners above the strict normal tolerance; two pallets fail their strict normal tolerance. Those reports were not suppressed or reinterpreted as visual passes.

## Offline/mock tests

From this folder:

```console
python -B -m unittest discover -s tests -v
```

The fixture and fake Unreal API test policy, counts, guards and failure reporting without installing Unreal or importing source art. They do not substitute for the guarded UE 5.7.4 run. See `VALIDATION.json` for tested scope and `CHECKSUMS.json` for the bounded delivered-file hashes.

## API references

- [UE 5.7 Material](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Material?application_version=5.7)
- [UE 5.7 TextureFactory](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/TextureFactory?application_version=5.7)
- [UE 5.7 LightComponent](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/LightComponent?application_version=5.7)
- [RectLight limitations](https://dev.epicgames.com/documentation/en-us/unreal-engine/rectangular-area-lights-in-unreal-engine?application_version=5.7)

The two support helpers are vendored unchanged and their hashes are checked at runtime. Use only the public functions in `carnival_full_import57`; the support helpers' standalone entry points are calibration-specific.
