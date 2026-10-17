# Full carnival import for Unreal Engine 5.7.4

This corrected importer creates a new, unsaved world and `/Game/AbandonedCarnivalFull57_Corrected`. The earlier full attempt stopped on the first asymmetric tile: its Y bounds were reflected, and a later read confirmed the reflection persisted after compilation. The three earlier calibration props had symmetric Y bounds, so their passing bounds checks did not establish handedness. The corrected axis transport has now passed two asymmetric native Unreal sentinels, including signed MeshDescription landmarks with zero error. The full scene has not yet completed import or visual/gameplay review.

The original 101 partial assets under `/Game/AbandonedCarnivalFull57` are left untouched. Do not rerun the old importer or delete those assets automatically. This revision uses a separate namespace and retains the original source FBXs, Blender source and the calibration map. A strict wrapper around the unchanged vendored validator now recognizes the observed legacy dot-to-underscore spelling while preserving strict order and rejecting ambiguous aliases.

## Exact scope

- 138 canonical prop meshes, placed as 153 separate native StaticMeshActors with their source PropActor tags.
- 43 environment meshes/actors. Eight intentionally have no collision.
- 59 materials, including one documented translucent glass approximation; 41 texture/usage assets.
- 10 native PlayerStarts and 41 source lights: 33 PointLights, 7 RectLights, 1 DirectionalLight.
- Total: 281 content assets and 247 authored actors, plus Unreal's world infrastructure.
- No Blueprints, existing-asset replacement, save, delete, cleanup, automatic retry, or renderer/exposure setting changes. Fresh import creates a new world; explicit recovery continues only its verified empty partial world. The saved calibration content stays separate.

All original FBX, texture and metadata files are checked against the pinned original FILE_MANIFEST. The original source's 15 parts are verified by their hashes and their combined source hash. JSON/Python pins permit only CRLF-to-LF normalization; binary hashes remain exact. Additional importer files do not require changing the frozen FILE_MANIFEST.

## Resume the verified second-attempt checkpoint

The second run created 41 textures, 59 materials and 68 meshes, then stopped on the first teddy because Unreal changed `.001` to `_001` while retaining spaces in imported material-slot names. The axis correction worked; this was an overly narrow name validator. No actors were created.

For that exact unchanged partial attempt, keep Unreal open on its empty `/Temp/Untitled_3.Untitled` world. Do not rerun `import_full`, delete partial assets, or save/rename the temporary world before recovery. Stop Play/Simulate. Pull the updated helper files, then use this explicit recovery command:

```python
import sys,json,importlib; sys.dont_write_bytecode=True; root=r"G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival"; sys.path.insert(0,root+r"\full_import57"); import carnival_full_import57 as f; f=importlib.reload(f); full_report=f.resume_full(root); print(json.dumps({k:full_report.get(k) for k in ("status","world_path","counts","validation","errors")},indent=2))
```

Recovery accepts only the known checkpoint: the exact empty temporary world, exact 168-asset inventory, pinned source/cache bytes and valid texture/material/mesh readbacks. The 65 already assigned meshes must retain their exact materials. Both early sentinels and the failed teddy may retain only approved importer defaults; recovery finishes their assignments. It imports the 113 missing meshes, then places the scene. Unexpected assets, edits, actors, sources, collision, slots or unrelated dirty work block recovery before mutation.

Existing material settings are checked; the successful creation ledger supports their graph provenance, but material graph retraversal and rendered appearance are not verified. Do not use this recovery for a modified or different partial attempt. No automatic deletion, asset replacement, save or rollback occurs. If blocked, share the report rather than repeating the command. Expected success is `FULL_RESUME_CREATED_UNSAVED`; a pre-mutation mismatch returns `FULL_RESUME_BLOCKED`, while an interruption after continuation reports `FULL_RESUME_FAILED_PARTIAL`. After success, inspect and manually save to `/Game/AbandonedCarnivalFull57_Corrected/Maps/AbandonedCarnivalFull57`.

## Before a fresh import

1. Pull the approved `full_import57` folder into your existing package root. Keep all nine delivered files together; no dependency installation is required.
2. Use Unreal **5.7.4**, with the same Editor Python setup used for calibration. Stop Play/Simulate.
3. Manually save any wanted calibration work, the previous 101 partial assets and current temporary map, or discard unwanted edits yourself. Preflight blocks any dirty map or content package; it will not silently discard the current world. The old failed mesh can be retained for comparison.
4. `/Game/AbandonedCarnivalFull57_Corrected` and its physical Content folder must not exist. A partial prior attempt is deliberately blocked. Inspect it before deciding manually what to retain/discard.
5. Source RectLights require deferred rendering. Forward rendering is blocked; this helper never changes it. Close other heavy applications if memory is tight. The full import is much larger than calibration.

## Read-only preflight

Run this in the Unreal Python console (one line). It does not create assets, actors, maps, or report files:

```python
import sys, json, importlib; sys.dont_write_bytecode = True; root = r"G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival"; sys.path.insert(0, root + r"\full_import57"); import carnival_full_import57 as f; f = importlib.reload(f); full_preflight = f.preflight(root); print(json.dumps({k: full_preflight.get(k) for k in ("status", "engine_version", "verified_file_count", "errors")}, indent=2))
```

Expected inside Unreal: `FULL_PREFLIGHT_PASS`. Outside Unreal, `FILES_VERIFIED_ENGINE_NOT_CHECKED` verifies source files only. A successful preflight does not authorize a cached bypass: import repeats all checks.

## Explicit full import

The optional preflight is also repeated internally. This complete one-line command reloads the updated module, then calls the single mutating entry point:

```python
import sys, json, importlib; sys.dont_write_bytecode = True; root = r"G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival"; sys.path.insert(0, root + r"\full_import57"); import carnival_full_import57 as f; f = importlib.reload(f); full_report = f.import_full(root); print(json.dumps({k: full_report.get(k) for k in ("status", "world_path", "counts", "validation", "errors")}, indent=2))
```

The importer creates a **fresh blank unsaved map** and first imports two asymmetric geometry sentinels: `SM_Env_Tile_m3_m4` (zero hulls) and `SM_OpenToolbox_20d6fff596` (21 hulls). Both must pass unchanged source bounds, UV, material-slot and UCX checks **before** any texture/material creation. Where documented MeshDescription getters are available, signed source-vertex landmarks are checked too; unavailable optional bindings are reported, not invented. It then automatically continues with textures, materials and the remaining 179 meshes. The Output Log reports each stage/count. Tasks remain sequential. Actual returned asset paths, legacy importer provenance, verified derived source filenames, texture settings, ordered slots, UV counts, centimetre bounds and exact UCX counts are checked. No auto-generated or complex-as-simple replacement collision is used. All solid actors block Pawn and Visibility; zero-hull decoration has collision disabled. These are structural settings, not a gameplay test.

Success is `FULL_IMPORT_CREATED_UNSAVED`. Wait for Unreal's background compilation, inspect the log and scene, then manually Save As:

`/Game/AbandonedCarnivalFull57_Corrected/Maps/AbandonedCarnivalFull57`

Save wanted content manually. The helper performs zero Unreal asset/map saves; it does write the explicitly described derived import cache below. Unreal's independent autosave is unchanged and may still occur.

Failure raises `FullImportError` with a structured `.report` and prints that report in the exception. It lists attempted/created assets and actors, current namespace contents, failure stage and partial-import status. Partial content is left for inspection. Do not rerun over it. No existing map or asset assignments need rollback because all mutations target newly created full-import content.

## Read-only check after import or manual save

With the full map open:

```python
full_audit = f.validate(root); print(json.dumps(full_audit, indent=2))
```

Dirty packages are allowed and listed. This validates the existing inventory, source provenance/settings, mesh/material assignments, actor transforms/tags, collision settings, light properties and source forward/up vectors. It does not re-traverse material graphs or establish shader compilation, visual quality, light matching, player clearance, multiplayer behavior or performance. `visual_pass` remains false until a separate human review; `FULL_STRUCTURE_PASS` is structural only.

## Deterministic import-only coordinate correction

The persistent reflection is observed UE 5.7.4 behavior. Legacy FBX handedness conversion is the supported explanation; the exact internal implementation was not inspected in the installed engine. Scene-axis conversion being disabled did not prevent the observed Y reflection.

A standard-library FBX7400 adapter compensates in derived copies only:
- Negate Y for every render/UCX vertex and explicit normal vector; keep X/Z and all other floating values unchanged.
- Reverse each polygon's corner order, move normal/UV indices with the same corner permutation, and preserve polygon material/smoothing order.
- Remap FBX Edges to retain the same endpoint pairs; preserve model/connection identities, scalar/string values and the binary footer.
- Leave UV values, texture pixels/green-channel settings and unit actor scale unchanged. No negative actor/build scale or relaxed bounds are used.

All 181 files / 2,457 render+UCX geometries passed independent offline per-corner association and edge-endpoint checks. Applying the adapter twice restored each original file byte-for-byte. These tests validate transport preparation, not native rendering or Chaos behavior.

New files are written exclusively under:

`<project Saved>/CarnivalFull57Derived/counter_y_fbx7400_v1/<original FBX SHA256>/`

Each source gets one derived FBX plus one deterministic metadata JSON. Originals are rehashed before derivation. Existing identical cache bytes can be reused; unexpected bytes or symlinks are refused, never overwritten. The report records original/derived hashes, import source paths and each cache file written. Keep these derived import sources with the project if you need reimport/audit later. Read-only preflight creates no cache; read-only validate checks existing cache and refuses to recreate missing files.

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
