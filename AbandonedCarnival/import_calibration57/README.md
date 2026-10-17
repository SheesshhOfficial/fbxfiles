# Carnival calibration importer for Unreal 5.7.4

Start with **START_HERE.txt**. Run only its read-only preflight, then share the result. Do not run the sample import or the published full importer yet.

This is a separate, local calibration patch. It does not modify the frozen source/export files. It has passed offline and mocked tests; **it has not been executed in Unreal**. A preflight pass does not establish successful import or gameplay.

## Install and read-only preflight

Extract the patch's `import_calibration57` folder into:

`G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival`

In Unreal 5.7.4's Output Log, choose Python and run this single line. The bytecode flag prevents Python from writing a helper `__pycache__` during module import; the preflight itself does not write files.

```python
import sys,json; sys.dont_write_bytecode=True; sys.path.insert(0,r'G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival\import_calibration57'); import carnival_calibration57 as c; report=c.preflight(r'G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival'); print(json.dumps({k:report.get(k) for k in ('status','ready_to_import','engine_version','error')},indent=2))
```

The complete in-memory report remains in `report`. To inspect it without saving a report file:

```python
print(json.dumps(report,indent=2))
```

Expected statuses:

- `PREFLIGHT_PASS`: source/sample hashes and available editor API/state checks passed. No import has run.
- `PREFLIGHT_BLOCKED`: stop and share the error. Do not bypass a guard or delete existing work to make it pass.
- `FILES_VERIFIED_ENGINE_NOT_CHECKED`: normal Python outside Unreal verified the files only; `ready_to_import` is false.

The exact target is UE **5.7.4**, not a blanket compatibility claim for 5.7/5.8. The Python Editor Script Plugin and Editor Scripting Utilities must be available. The helper never installs/enables plugins or changes project/editor preferences.

## What preflight verifies

- Five pinned JSON documents: prop manifest, file inventory, source-parts index, frozen-source record and prop fidelity evidence.
- Raw JSON hashes must match, with one explicit Windows checkout allowance: CRLF converted to LF may match the pinned bytes. Any such file is listed in `normalized_json_files`. This is not general JSON reformatting tolerance.
- Exact full-file binary hashes for the three sample FBXs.
- Every source part's hash/size and the SHA256 of the **entire concatenated source stream**, 136,393,382 bytes. It does not assemble or open Blender. All 15 packaged source parts must remain available.
- The frozen source SHA256 is `2d4f00dbf3704895a79ea30287dfa93ac7d0ad87f6e03e0e1ea163888418ca1a`.
- Required Unreal classes, methods, enum members and read-only reflected properties, including aggregate collision arrays.
- No dirty map/content packages, no Play/Simulate session, and no pre-existing target namespace, assets, map or calibration actors. A physical existing Content folder also blocks the run, even if empty.

It hashes the sample dependencies and source, not every unrelated texture/environment export in the package. Read-only default-object inspection does not configure import options or create assets/maps. Reports are returned in memory; there is no report-file writer.

## Later explicit sample step

This command is provided for the later, separately approved sample stage. **Do not run it as part of the first preflight.** It changes the open editor world and creates new unsaved assets/actors.

After reviewing a passing preflight and deliberately choosing to proceed:

```python
sample_report=c.import_sample(r'G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival'); print(json.dumps(sample_report,indent=2))
```

Exactly three canonical mesh assets are imported:

| Mesh | Authored convex UCX hulls | Source material slots | UV channels |
|---|---:|---:|---:|
| SM_BumperCar_566477cf32 | 8 | 6 | 1 |
| SM_wooden_pallet_244700516e | 9 | 2 | 1 |
| SM_OpenMaintenanceBucket_aeb36301a9 | 1 | 2 | 1 |

Four independent native `StaticMeshActor` placements are made. The bucket's second actor references the **same bucket mesh asset**. All preserve `PropActor`; no Blueprint is created. They are clearly spaced: car at X=0, pallet at X=500, bucket at X=1000 cm, plus the duplicate bucket at Y=350 cm. Their local bottom bounds are positioned at Z=0. There is no floor asset, light or player start.

The only asset namespace is `/Game/AbandonedCarnivalCalibration57/Props`. A fresh blank map is opened through `new_blank_map(False)` only after guards pass. It is an **unsaved transient map**, not a map already saved at a fixed content path. If you later choose to retain it, the suggested manual Save As path is `/Game/AbandonedCarnivalCalibration57/Maps/Calibration57`.

The importer never calls a save API, including on success; it does not change the editor's independent autosave settings. It never overwrites, deletes, renames around a mismatch, or silently cleans up. A previous run blocks a repeat.

## Import and verification policy

- Explicit `FbxFactory`, synchronous `AssetImportTask`, static mesh type, no automated type detection, no replacement, no task save.
- `convert_scene=False`, `convert_scene_unit=False`, scale=1: these FBXs already contain UE-centimeter geometry with baked transforms. No second axis/unit conversion is applied.
- Source normals are imported; MikkTSpace tangents are generated. These FBXs contain normals but no tangent/binormal payload, so `IMPORT_NORMALS_AND_TANGENTS` would be inappropriate. Build settings explicitly preserve normals and recompute tangents. This is a configured policy, not proof of visual shading fidelity.
- No automatic collision, one convex hull per UCX, no generated lightmap UVs, no Nanite, and no LOD import.
- Result names/paths are checked against both `task.get_objects()` and `imported_object_paths`. Exactly one expected StaticMesh per task is allowed.
- Actual import provenance must be the legacy `FbxStaticMeshImportData` class and point to the verified input FBX. `FbxFactory` alone is not assumed to guarantee legacy routing.
- Bounds must match the source manifest per axis within the larger of 0.05 cm and 0.1% of that axis's size.
- Material-slot count and ordered imported names are checked against source names or one exact source-derived sanitizer. All visual slots receive the existing engine default material; no material or texture assets are built/imported.
- UV channel presence/count is checked. This does not compare every UV coordinate.
- Convex count is checked both through StaticMeshEditorSubsystem and BodySetup aggregate arrays. All box, sphere, capsule, tapered-capsule and level-set/other arrays must be empty. The aggregate's convex count must be exactly 8/9/1. The generic simple count is diagnostic only because its aggregate semantics are not assumed.
- New assets explicitly use SimpleAndComplex collision. No project collision defaults are edited. This does not test capsule movement, visibility traces or opening clearances.
- The UE 5.7-documented `coordinate_system_policy` is recorded; it is not guessed or overridden. LUF coordinate mode is rejected for this already-converted source.

`SAMPLE_GEOMETRY_COLLISION_PASS_UNSAVED` means these narrow editor checks passed. Materials, textures, lighting, collision clearance, gameplay, multiplayer, saved/reopened persistence and the full map remain unvalidated.

## Failures and partial state

`import_sample` raises `CalibrationError`; its `report` contains the stage, error, attempted/imported object identities and any recorded actors. `SAMPLE_BLOCKED` means no map/asset mutation started. `SAMPLE_FAILED_PARTIAL` means a new map, assets or actors may remain. A failed import can create objects before returning an error.

Inspect that partial state manually. Do not immediately rerun. The helper deliberately has no rollback or delete command, and it does not save a partly verified map. Existing work outside the calibration namespace is never an intended edit target.

## Offline tests

No installation or Unreal/Blender dependency is required. From the patch folder:

```text
python -B -m unittest discover -s tests -v
```

The mock suite uses synthetic temporary files and fake API objects. To also run the two real-package integration/hash checks on Windows Command Prompt:

```text
set CARNIVAL_PACKAGE_ROOT=G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival
python -B -m unittest discover -s tests -v
```

Without a package path, the two integration tests skip unless the original local staging layout is present. The other tests remain standalone. Tests use temporary directories; the importer does not.

Recorded local result: **27 tests passed**, including real frozen-source/sample hash checks and mocked success, dirty-state, existing-target, version, missing API, Interchange, bounds, collision, UV, slot order, partial failure and line-ending cases. These are offline/mock results, not an Unreal runtime pass.

Standalone read-only file check:

```text
python -B carnival_calibration57.py "G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival"
```

The script's command-line entry only runs preflight. It has no full-import mode.

## Epic API references checked for this patch

- [UE 5.7 FbxImportUI](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxImportUI?application_version=5.7)
- [UE 5.7 FbxStaticMeshImportData](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxStaticMeshImportData?application_version=5.7)
- [UE 5.7 AssetImportTask](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetImportTask?application_version=5.7)
- [UE 5.7 EditorLoadingAndSavingUtils](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorLoadingAndSavingUtils?application_version=5.7)
- [UE 5.7 KAggregateGeom](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/KAggregateGeom?application_version=5.7)
- [UE 5.7 StaticMeshEditorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMeshEditorSubsystem?application_version=5.7)
- [UE 5.7 FBX import options](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-import-options-reference-in-unreal-engine?application_version=5.7)

The property spelling `using_luf_coordinate_sysem` follows Epic's 5.7 Python API exactly. Availability still must pass the actual editor reflection checks. Documentation and mocks cannot establish runtime success.


## GitHub updates and current progress

Before the first pull, rename any manually extracted untracked `import_calibration57` folder to an unused backup name and retain it. Then run `git -C "G:\Unity Projects\Generated\fbxfiles" pull --ff-only`. Never use force-reset or git clean to resolve a conflict. Future pulls update these tracked helpers normally. No imported Unreal asset is changed by a Git pull.

Geometry and material stages have now completed in the user's Unreal 5.7.4 editor: exact mesh bounds, UCX counts8/9/1, ten verified textures, nine materials and three neutral lights. Do not rerun import_sample/apply on this successful sample. Review the screenshot with fixed viewport exposure: bright pallet/highlights are not yet visually approved. Shader completion, close-range fidelity and gameplay remain unverified. These scripts explicitly save nothing; Unreal's own autosave may operate independently.

This helper snapshot excludes all full-map metadata correction scripts. The original package FILE_MANIFEST.json is unchanged; HELPER_MANIFEST.json covers only this additional calibration folder.
