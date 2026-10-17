# Carnival Unreal 5.7 import review

The Blender source is unchanged. This review concerns the prepared Unreal Python import helpers, which have not run in the target editor. Do not start the published full-map importer before a calibration test.

## Existing published entrypoints

In `AbandonedCarnival/export/unreal/`:

- `import_carnival.import_carnival(root=None)` imports the entire package, with no sample mode.
- `import_environment.import_environment(root=None, level_path=DEFAULT_LEVEL, create_level=True, allow_existing=False)` imports all scenery.
- `import_props.import_props(root=None)` imports all props and places them in the currently open level. Do not run this directly in an existing game map.
- `import_materials.build_materials(root=None)` builds all prepared materials.
- `import_scene_metadata.import_scene_metadata(root=None, level_path=DEFAULT_LEVEL, local_lumens_per_blender_watt=100.0, directional_lux_per_blender_unit=1.0, attenuation_radius_cm=1200.0)` adds starts and approximate lights.

`root` for these published helpers means the `export/unreal` directory. The new calibration helper instead accepts the outer `AbandonedCarnival` package directory.

A full import would produce 43 environment actors, 153 individual eligible prop actors backed by 138 canonical prop assets, 10 PlayerStarts and 41 lights, with 59 prepared materials. The proposed content root is `/Game/MoonfallCarnivalV2/`; the proposed full-map path is `/Game/MoonfallCarnivalV2/Maps/MoonfallCarnival`.

## Confirmed corrections and required checks

1. The published metadata helper passes `[pitch,yaw,roll]` positionally to `unreal.Rotator`, whose UE5.7 Python positional order is `(roll,pitch,yaw)`. A locally reviewed correction uses explicit keywords; that full-map correction is intentionally excluded from this calibration-only publication. All 51 exported rotation bases were reconstructed offline; maximum component error was 1.48e-7. Actual spawned Unreal orientations remain untested. All seven RectLights and the directional light need visual/basis verification; current PlayerStarts use zero rotations.
2. Mesh and texture imports configure destination names but do not verify their importer path. Interchange may ignore `destination_name`; legacy FBX options cannot be assumed applied. Explicit factory selection must be followed by checking actual task results, asset path and import-data type in the editor.
3. Published helpers do not validate imported UCX counts, actual centimeter bounds or material-slot ordering. Component collision responses alone do not prove collision geometry imported correctly. The sample will check those first.
4. The current FBXs contain source corner normals but no tangent payload. Import normals and generate MikkTSpace tangents; do not claim imported tangents exist.
5. The material builder needs a separate smoke test: actual texture naming, non-virtual textures with ordinary sampler types, UV0, normal green-channel convention, tint wiring and shader compilation. `recompile_material()` is not a shader-success report. Glass is approximate.
6. Light conversion factors are uncalibrated estimates. Blender world/fog/compositing and render-only atmosphere are not reproduced automatically. Do not bulk-import all movable lights before checking exposure and cost.

## Safe sequence

- Use a disposable test project or a separately backed-up project, a fresh editor session, and enable Python Editor Script Plugin plus Editor Scripting Utilities. Save or resolve existing dirty maps/content yourself.
- Run the calibration module's read-only `preflight(package_root)` first. It must not import, save, create maps/assets, or change settings. Return its printed result before proceeding.
- If preflight passes, explicitly run `import_sample(package_root)`. This is a geometry/collision-only test of three assets and four separate actors: one bumper car, one pallet, and two copies of the same bucket mesh. It does not validate textures, lighting, the full carnival, gameplay, or multiplayer.
- Inspect source normals under raking light, the bumper cockpit and pallet openings, and each bucket's actor identity. Then perform separate material/texture, scenery and lighting calibration before any reviewed full importer.
- Keep BP_propChar unchanged. The existing single-hit Visibility trace may return scenery first and reject it; test this in the real game project rather than changing the Blueprint implicitly.

## Evidence and limits

Frozen source SHA256: `2d4f00dbf3704895a79ea30287dfa93ac7d0ad87f6e03e0e1ea163888418ca1a`.

Raw FBX source normals match the authored data. Blender reimport still has documented normal reconstruction differences in 24 scenery tiles and two pallet assets. The actual Unreal importer and generated tangent basis need inspection. No runtime performance, Chaos cooking, navigation, possession or replication success is claimed.

The corrective files in this patch are separate from the published V2 source. No automatic full-map import is included in the initial calibration workflow.

## Official API references

- [Rotator constructor](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Rotator?application_version=5.7)
- [AssetImportTask and Interchange naming caveat](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetImportTask?application_version=5.7)
- [FBX static-mesh import settings](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxStaticMeshImportData?application_version=5.7)
- [Static mesh editor collision/UV queries](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMeshEditorSubsystem?application_version=5.7)
- [TextureFactory](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/TextureFactory?application_version=5.7)
- [Texture2D settings](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Texture2D?application_version=5.7)
- [Material editing and compilation](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary?application_version=5.7)
