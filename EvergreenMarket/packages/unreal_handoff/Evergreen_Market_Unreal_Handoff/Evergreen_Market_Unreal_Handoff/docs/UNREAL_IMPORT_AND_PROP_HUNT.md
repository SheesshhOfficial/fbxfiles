# Evergreen Market: Unreal import and prop-hunt integration

## What is delivered and what remains

This is a geometry/material handoff and an **editor import helper**, not an Unreal project or implemented multiplayer game. The helper's Python syntax and pure-data tests pass locally. **Unreal Engine was unavailable: UE import, component persistence, orientation, visual fidelity, gameplay, and multiplayer are not runtime-tested.** The helper checks those import properties it can when you run it, and stops on mismatches.

The new Blender scene retains authored material nodes. Unreal materials approximate uniform PBR properties and reuse original PNG labels. Procedural noise/bump, transmission/refraction, Blender lighting, and renderer-specific effects are not reproduced exactly. Relight the level in Unreal. In the generated staging map, use an Unlit viewport to inspect geometry before adding lighting.

## 1. Run a representative import first

Use a disposable project copy or a source-control checkpoint. Enable **Python Editor Script Plugin** and **Editor Scripting Utilities**, then restart the editor. This script targets the documented UE **5.7 Python API**; Python is an editor production tool, not the runtime gameplay implementation. Other UE versions may require API adjustments. [Epic: Python editor scripting](https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python)

1. Extract the whole package; keep `manifest.json`, `materials.json`, `assets/`, `textures/`, and `source/` together.
2. Save or discard your existing unsaved maps/content yourself. Stop Play In Editor. The script refuses to proceed with dirty packages.
3. Open **Output Log**, select its **Python** input mode, and enter the following, replacing the example path:

```python
import sys
sys.path.insert(0, r"C:\Art\EvergreenMarket\source")
import import_supermarket_unreal as em
package = r"C:\Art\EvergreenMarket"
em.run(package)  # Validates every referenced file and prints a dry-run plan only.
sample_report = em.run(package, execute=True, phase="sample")
```

The sample includes category representatives, textured and transparent materials, an asymmetric asset, a rotated placement, shipping carton/cart/chair families, a bottle/can, and floor/shelf meshes when present. It imports at most three transform variants per selected asset. Objects retain their actual scene positions; select a generated actor and focus it in the viewport.

The importer uses legacy `FbxImportUI` options. If it reports Interchange FBX is enabled, enter **Interchange.FeatureFlags.Import.FBX 0** in the editor's normal console, then retry. Record and restore your previous setting when done. The helper does not change importer settings itself. Interchange has a separate pipeline and can ignore legacy naming/options, so silently mixing both is unsafe. [Epic: Interchange import](https://dev.epicgames.com/documentation/unreal-engine/importing-assets-using-interchange-in-unreal-engine) · [AssetImportTask API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetImportTask?application_version=5.7)

4. Check the sample manually:
   - Carton label facing source Blender **−Y** should face UE **+Y**.
   - A cart handle toward source Blender **+Y** should face UE **−Y**.
   - Inspect a rotated chair. Check backrest, feet and orientation, not only its bounding box.
   - In the full scene, the loading yard remains **+X/east**, and the front entrance moves from source negative Y to **positive UE Y**.
   - Check readable label UVs, front/back faces, glass, material slots, dimensions and bottom-center pivots.
   - In Static Mesh Editor, inspect collision visualization. Check that boxes fit their specific props and that scenery marked `none` has none.

Bounds passing cannot prove handedness or correct label facing. Do not approve the full run until these asymmetric checks pass. On a mismatch, fix the export/import contract and rerun the sample; do not compensate by scaling/rotating the entire assembled map.

5. After review, run the full reconstruction in a separate generated folder:

```python
full_report = em.run(package, execute=True, phase="full",
                     preflight_report=sample_report,
                     visual_review_approved=True)
```

The full run requires a successful sample persistence report, coverage of the default representative set, matching SHA-256 fingerprints for the manifest/materials/FBXs/textures, and explicit visual approval. It creates a fresh timestamped `/Game/EvergreenHandoff/...` folder and a new staging map. It never overwrites/deletes existing assets. A failed partial run remains in its generated folder for inspection; retry into a fresh folder. Do not assume failure rolls back imports.

Reports and `instance_lookup.csv` are written under the project's **Saved/EvergreenHandoff/**. After constructing the new map the script saves, reloads, and checks every generated ISM's mesh, instance count, and world transform. `verified_persistence` means those checks passed in your editor; it does not certify the manual checks, performance, or gameplay. Creating/loading a map can discard the current unsaved level, which is why dirty-map guards precede transitions. [LevelEditorSubsystem API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/LevelEditorSubsystem?application_version=5.7) · [Dirty package API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorLoadingAndSavingUtils?application_version=5.7)

## 2. Exact package contract

- `manifest.json`: versioned asset and placement records. One FBX per **unique logical Static Mesh**, reused for placements; multi-part objects such as cartons/cart assemblies can be one logical asset.
- Local `bounds_cm` are full X/Y/Z dimensions, not half-extents. A zero thickness is allowed for a surface. Meshes use bottom-center pivots; placements carry the pivot's world position.
- Coordinates are already **UE centimeters, X-forward/Y-right/Z-up**. Source conversion is `[100*x, -100*y, 100*z]`. Do not multiply placements by 100 again. UE uses a left-handed coordinate system. [Epic: coordinates](https://dev.epicgames.com/documentation/en-us/unreal-engine/coordinate-system-and-spaces-in-unreal-engine)
- `quaternion_xyzw` is preferred. The helper creates `unreal.Quat(x,y,z,w).rotator()`. Fallback `rotation_deg` is `[pitch,yaw,roll]` in degrees and is passed using **named arguments**; UE Python's positional Rotator constructor order is roll/pitch/yaw. Scale is positive XYZ; mirrored/negative scale must be baked by the exporter. [Quat API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Quat?application_version=5.7) · [Rotator API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Rotator?application_version=5.7)
- This export's FBX flags are `convert_scene=False`, `convert_scene_unit=False`, `force_front_x_axis=False`, `import_uniform_scale=1`, `transform_vertex_to_absolute=True`. Import rotation/translation are zero. These are package-specific, not universal Blender settings. Import validation fails if dimensions/pivots disagree. [FBX options](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxStaticMeshImportData?application_version=5.7)
- `materials.json` has `schema_version:1` and a `materials` array keyed by each record's `material_id`. Required fields: linear `base_color_rgba`, `roughness`, `metallic`; optional original `base_color_texture`, `emissive_rgb` already multiplied by strength, `alpha_mode`, `opacity`, `two_sided`. A linked texture supplies base color directly. Explicit opacity overrides texture alpha. IDs equal the exported FBX material-slot names; assignments are matched by unique slot name. Every `used_materials` ID must survive, unknown/duplicate slots fail, and declared unused slots may be stripped by UE. [Material editing API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary?application_version=5.7)
- Collision strategy is explicit: `box` imports the associated `UBX_<render-mesh-name>_00` proxy; `none` stays collision-free. Automatic collision generation is disabled and imported simple collision counts are checked. Broad boxes are conservative starting points, especially on carts/fixtures. [Epic: FBX collision naming](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine) · [Collision count API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMeshEditorSubsystem?application_version=5.7)

## 3. Recommended hybrid: instanced scenery, real gameplay actors

The reconstruction creates **one actor/ISM component per asset per 20 m XY sector**, rather than one actor per placement. Change `sector_size_cm` only after profiling. Identical meshes share their mesh/material resources; component-level collision/material settings affect all instances in that component. ISM is a rendering/placement optimization, not an implementation of interactable behavior. [Epic: Instanced Static Mesh Component](https://dev.epicgames.com/documentation/unreal-engine/instanced-static-mesh-component-in-unreal-engine)

Use the prop shortlist accompanying this package to build an explicit allowed-disguise list. `fixed` entries are scenery. Other tiers are candidates, not automatically fair/approved disguises. Small products need minimum-size and visibility rules; large carts/fixtures need movement clearance checks.

- Keep repeated shelf products and stationary props as ISMs when the player only **copies their appearance**. Leave the source instance in place.
- The disguised player remains your real Character/Pawn. A movable StaticMesh component on it references the **same imported Static Mesh asset**, with replicated appearance state.
- Use ordinary Blueprint actors for the relatively few pickups, doors, physics objects, damageable props, or objects whose individual gameplay state changes. They can also reference the same Static Mesh. You do not need to duplicate the mesh asset.
- No project-specific player Blueprint, input mapping, RPC, or game rule is modified or generated by this package.

## 4. E-to-disguise integration outline

Implement this in your existing game after the sample import passes:

1. Create a `PropDefinition` Data Asset/Data Table row for each allowed `AssetId`: Static Mesh reference, permitted scale, visual offset, movement capsule size, weapon hitbox, camera offset, movement limits and eligibility tier.
2. Import `instance_lookup.csv` into a Data Table using a matching struct (`ComponentKey`, integer `InstanceIndex`, string/name `StableInstanceId`, string/name `AssetId`, float `LocationX/Y/Z`). CSV `Name` is the row key. The report retains complete transforms. JSON/CSV sitting in Saved are **not automatically cooked gameplay assets**; explicitly create/reference the Data Table in the project.
3. At level initialization register generated components by their **EMGroup=... component tag**. Use this stable tag plus the table to map local hit indices to stable IDs. Do not use editor actor labels as runtime identity.
4. Bind your Interact input (E, if desired). Trace from the local camera, ignoring the player. Break the result, require a valid ISM hit component, and use **Hit Item** as the local instance index for that hit. Hit Item is primitive-specific: verify its ISM-index mapping in your target engine with the actual trace/collision setup. Reject negative/out-of-range indices, confirm the current instance transform, then resolve through the registry. Trace results identify hit components and primitive-specific item data. [Epic: traces](https://dev.epicgames.com/documentation/en-us/unreal-engine/traces-in-unreal-engine---overview)
5. Send a **Server RPC on the client's owned Character/PlayerController**, carrying the stable source ID and requested allowed type. On the server independently resolve the source, validate eligibility, distance, line of sight, current player state and cooldown, and retrace as appropriate. Do not trust client mesh paths, arbitrary transforms, or a client-only hit. The proposed range (for example 250–300 cm) is a game-design choice to tune. [Epic: RPC ownership and execution](https://dev.epicgames.com/documentation/en-us/unreal-engine/remote-procedure-calls-in-unreal-engine)
6. Server applies the approved definition and replicates `DisguiseAssetId`, scale/variant and disguise state. Use RepNotify to rebuild appearance on clients, including late joiners. Appearance updates alone do not replicate arbitrary ISM changes or implement authoritative collision.
7. Place the bottom-center visual mesh at the character's feet. With a centered movement capsule, its initial relative Z offset is typically negative capsule half-height; verify your character hierarchy. Validate overlaps before changing capsule dimensions. Keep a supported movement capsule; use separate query hit geometry if weapon hits should match the prop silhouette. Do not simulate physics on a cosmetic character mesh.

**Stable-ID rule:** ISM indices can change after removal, reordering, regeneration or streaming/rebuild work. Keep the exported `instance_id` as a string/name and maintain authoritative stable-ID-to-current-instance mappings. For a static immutable copy-only map, the saved table is sufficient after persistence checks. If you remove/promote/move sources, update mappings and replicated state on the server. A raw index is not a network/save-game ID. Do not encode GUIDs or large integer IDs into float custom-data channels.

## 5. Collision and playtest gate

The import is a **staging scene**: `box` instances are Query Only and block Visibility; `none` instances have No Collision. Pawn movement is not configured. Add/review floor/wall/fixture movement collision and your project's trace channel before treating it as playable.

For selection, create a dedicated `PropInteract` trace channel/preset. Eligible products must be traceable individually. Shelf-wide collision boxes must not intercept every product trace: ignore them on PropInteract or replace them with shelf-board/support collision. Keep a separate visibility/occlusion check so interaction cannot pass through real walls or closed containers. Collision should match the intended hollow/solid behavior; a single box often fills useful gaps. [Epic: Static Mesh collision](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-collisions-with-static-meshes-in-unreal-engine)

Before shipping: test aiming at products behind shelf edges, tiny versus large disguises, blocked transformations, slopes/doorways, restoration to normal appearance, duplicate/invalid IDs, removal mapping, server rejection, two clients, late join, death/respawn, and map reload. Profile draw calls, materials, triangles, collision, shadows and memory on target hardware. ISM alone is not a frame-rate guarantee.

## Implementation references and local checks

Persistent component creation uses editor `SubobjectDataSubsystem.add_new_subobject` on each generated actor, rather than allocating transient Python UObjects. Transform insertion uses `add_instances(..., world_space=True)` and stores the actual returned indices. Reload checks detect missing components or lost placements. [SubobjectDataSubsystem API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/SubobjectDataSubsystem?application_version=5.7) · [Subobject data library](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/SubobjectDataBlueprintFunctionLibrary?application_version=5.7) · [ISM Python API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InstancedStaticMeshComponent?application_version=5.7)

Local checks, independent of Unreal:

```sh
python -m py_compile source/import_supermarket_unreal.py
python -m unittest discover -s source -p 'test_import_contract.py' -v
```

`IMPORTER_LOCAL_TEST_RESULTS.txt` records 16 pure-data tests. They cover valid planning, path containment, missing files, duplicate IDs, unknown material references, non-finite transforms, invalid quaternions, negative scales, flat surfaces, binary fingerprint changes, sample/full counts, the full-import approval gate, and safe material-slot matching with unused slots. These tests do **not** mock or certify Unreal API execution.
