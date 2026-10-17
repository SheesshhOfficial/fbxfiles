# Sample materials and neutral lighting, UE 5.7.4

This is an additive second stage. Keep the original `carnival_calibration57.py` unchanged. Place this `material_stage` folder inside the existing `import_calibration57` folder.

Prerequisite: the successful three-mesh/four-actor geometry sample must be saved by you at `/Game/AbandonedCarnivalCalibration57/Maps/Calibration57`, with its three mesh assets also saved. Leave that map open, stop Play/Simulate, and finish saving or discarding any other unsaved work yourself.

## Read-only check

Paste this one line into Unreal Output Log's Python field:

```python
import sys,json; sys.dont_write_bytecode=True; sys.path.insert(0,r'G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival\import_calibration57\material_stage'); import carnival_material_stage57 as m; material_check=m.preflight(r'G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival'); print(json.dumps({k:material_check.get(k) for k in ('status','ready','engine_version','error')},indent=2))
```

Only `MATERIAL_PREFLIGHT_PASS` means the read-only editor guards passed. If blocked, share the error; do not weaken guards or delete existing assets. Outside Unreal, `FILES_VERIFIED_ENGINE_NOT_CHECKED` only verifies the source files.

## Explicit material/light step

After choosing to proceed with the material stage, run:

```python
material_report=m.apply(r'G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival'); print(json.dumps(material_report,indent=2))
```

This creates **10 textures and 9 materials** under the new `/Game/AbandonedCarnivalCalibration57/MaterialStage` folder, assigns those materials to the saved sample meshes, and adds three neutral lights to the sample map. The duplicate bucket still shares the same mesh. No Blueprint, full-map import, renderer preference, project setting, exposure setting or source export is changed.

Nothing is automatically saved. The existing sample meshes' material assignments and sample map become unsaved changes. The helper neither overwrites existing material/texture assets nor deletes objects. An existing MaterialStage folder blocks a repeat.

Expected completion: `MATERIAL_STAGE_CREATED_UNSAVED`. This means object creation, graph connections and assignment readbacks completed. It does **not** mean shader compilation or the visual result has passed.

## Source recipe and texture handling

The exact source definitions are taken from the frozen package's `material_manifest.json`. The subset is PaintRed; ride rubber, nickel, oxblood enamel, charcoal vinyl and old headlamp glass; wood, rust and black. The material named old headlamp glass is **opaque in the actual source definition** (`transmission=0`, `glass_approximation=false`), and remains opaque here.

Source and manifest hashes are checked. Ten selected texture files must match the frozen file inventory's complete binary SHA256 and size. Pinned JSON permits only CRLF-to-LF normalization to accommodate Windows checkout line endings; texture/source binary hashes remain exact.

Texture imports use explicit `TextureFactory`, no material creation, synchronous single-task submissions, no replacement or save. Actual task object identities and paths must match; actual import data must be native `AssetImportData`, with the correct input filename. Interchange or other unexpected import-data classes stop the stage. No guessed load, rename or fallback is used.

Textures are explicitly non-virtual, with sRGB/compression/normal green-channel settings matching their roles. Graph samplers match those settings, using UV channel 0 at scale 1. Source roughness/metallic/emission/constants and any source tint are preserved. Each material graph requests compilation.

Imports are submitted **one at a time** because compilation memory was a concern. Unreal can still do texture/shader work in the background; this does not guarantee low peak memory or that compilation is complete. Wait for the editor's remaining compilation activity before judging the result. Do not rerun while it works.

## Neutral viewing lights

- White movable directional key: 1000 lux, pitch -45°, yaw 45°, shadows on.
- Two white movable point fills: 8000 lumens each, inverse-squared falloff, 2000 cm attenuation radius, shadows off.
- No sky/reflection capture, extra floor, player start or gameplay setup.

These are simple material/normal-response lights, compatible with forward or deferred rendering. They do not reproduce Blender lighting. Metal reflections and the final environment are not validated in this empty sample map.

Inspect in **Lit** mode. For stable A/B comparison, you can manually disable the viewport's game/automatic exposure and hold its exposure fixed, starting around EV100 8 and adjusting once for a readable image. That is a viewing suggestion; the helper does not change exposure. Keep the same exposure when comparing runs. Check the source-colored car, rubber/vinyl contrast, wood and rust surfaces, normal direction, and both buckets. If materials stay gray or look wrong, share the report and a screenshot after compilation finishes.

## Failure and recovery

`MaterialStageError.report` records the failed stage, created/attempted assets, assignments and lights. Before assignment, the original material object in every sample mesh slot is captured. If a later assignment/light step fails, the helper attempts to restore those original assignments and verifies each restoration. It does not assume the originals are the default material.

Read the `rollback` entries: any `FAILED` restoration needs manual inspection. Restored mesh packages can still be dirty. New material/texture assets and any lights remain for inspection; there is no cleanup or save. A partial run blocks an automatic retry.

No component material overrides are altered: preflight rejects an unexpected override. It also checks the exact saved world, three expected meshes, four distinct native sample actors with preserved `PropActor` tags, no unrelated authored actors, clean editor state, no PIE, and an unused destination.

## Offline tests and limits

From this folder:

```text
python -B -m unittest discover -s tests -v
```

Tests use standard-library mocks; no dependencies are installed. Real-package integration tests use `CARNIVAL_PACKAGE_ROOT` when configured. **Offline mocks do not establish Unreal runtime success.** Material compilation, visual fidelity and final lighting still require the actual editor check. Gameplay, collision clearances, full-map behavior, saves/reopen and multiplayer are outside this stage.

Epic references: [TextureFactory](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/TextureFactory?application_version=5.7), [Texture2D](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Texture2D?application_version=5.7), [AssetImportData](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetImportData?application_version=5.7), [PointLightComponent](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PointLightComponent?application_version=5.7), [LightComponent](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/LightComponent?application_version=5.7).
