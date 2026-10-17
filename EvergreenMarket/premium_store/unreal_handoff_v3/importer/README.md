# Refined v3 → Unreal 5.8: sample first

**This importer has not been run in Unreal.** Offline tests and Blender FBX round-trips are separate evidence. Treat the first engine import as calibration, never as gameplay acceptance. Do not use the old pilot/ISM helper.

The package root is `C:\Art\EvergreenMarket_v3`, containing `export`, `qa_axis`, and `importer`. Your project is `G:\Games\SheeshhPropHuntYT`. The approved source remains the separately delivered `YOU_WANT_IT_YOU_GET_IT_REFINED_v3.blend`, SHA-256 `c4abf30a478051c30e00536642416c53fefb7db4911128dbb8114c0732975519`. No existing project asset, map, Blueprint, GameMode, collision profile, or project setting is overwritten. Failed attempts leave only a new partial version folder; use a fresh version for another attempt.

## 1. Prepare and inspect without changing Unreal

Extract to a fresh `C:\Art\EvergreenMarket_v3` folder. Do not merge with an older handoff. The supplied downloader handles checksum verification and fresh-folder extraction; its Windows execution is also untested here.

Optional offline Python commands from PowerShell:

```powershell
py -3 -m unittest discover -s C:\Art\EvergreenMarket_v3\importer\tests -v
py -3 C:\Art\EvergreenMarket_v3\importer\store_importer.py --package C:\Art\EvergreenMarket_v3 --phase sample --destination /Game/PremiumStoreV3/Sample_v001 --output C:\Art\EvergreenMarket_v3\sample_plan.json
```

The CLI is **dry-run only**. Its output refuses to overwrite an existing file. If Python is not separately installed, use `dry_run` in Unreal below. No need to install another Python for this package.

Open the project in **Unreal Editor 5.8.x**. Enable Python Editor Script Plugin and Editor Scripting Utilities if necessary, then restart the editor. Save or discard your existing dirty assets/maps yourself. Stop PIE before running editor scripts. Keep a project backup or clean source-control checkpoint.

In the Output Log's **Python** input, run these as separate commands:

```python
import sys
sys.path.insert(0, r"C:\Art\EvergreenMarket_v3\importer")
import store_importer as v3
plan = v3.dry_run(r"C:\Art\EvergreenMarket_v3", phase="sample", destination="/Game/PremiumStoreV3/Sample_v001")
print(plan["expected_placement_count"], plan["expected_eligible_count"], plan["full_material_blockers"])
```

Dry-run validates approved-source lineage, every FBX/texture digest, passing export/reimport evidence and source counts, unique placement IDs, individual StaticMeshActor contracts, explicit materials/UV bindings, 67 fixture-light rows and boundary/spawn metadata. Full-stage material blockers are shown even when the blocked material is outside the sample. Stop and resolve any blocker; do not turn it into a placeholder or bypass the guard.

## 2. Create only the calibration sample

This is the first command that creates Unreal content:

```python
report = v3.run(r"C:\Art\EvergreenMarket_v3", phase="sample", destination="/Game/PremiumStoreV3/Sample_v001")
print(report)
```

It creates `/Game/PremiumStoreV3/Sample_v001/Maps/L_V3_CalibrationSample` in a new non-World-Partition map. It never opens or replaces an existing destination. If `Sample_v001` already exists, choose `Sample_v002` and use that version's report paths in the following steps.

The bounded sample uses actual authored positions: at least three separate copies of the same can; floor, wall, shelf, basket, chair, shopping cart, service counter and large carton; textured/normal and optical examples; one mounted refined v3 sign with lettering, carrier and hardware; one refined tree; and the separate asymmetric axis probe. All 67 fixture lights, ten actual PlayerStarts, four boundary metadata TargetPoints and four invisible perimeter barriers are included. The sample has incomplete visual geometry, while its four perimeter barriers already contain the authored interior footprint.

The importer checks every newly imported local bound/pivot, triangle count, UV count, material-slot identity/order, exact UCX convex count and absence of extra collision shapes. It then spawns separate actors, saves the map, reloads it and rechecks actor IDs/counts, class, Prop tags, transforms, shared canonical mesh references, collision responses, material assignment/policies, texture import flags, fixture lights, PlayerStarts, boundary metadata markers and invisible barrier dimensions/flags. This in-session map reload is not a cold asset-package test.

### Axis calibration is mandatory

Select `V3_QA_AXIS_PROBE` in the Outliner and press F. Its actor origin is `(-500, 500, 0)` cm. Relative to that origin:

- Red bar reaches **+100 cm X**
- Green bar reaches **−200 cm Y**
- Blue bar reaches **+300 cm Z**

Its three bars have asymmetric geometry, three source material slots and three UCX hulls. Check units, color direction, handedness and lower-corner pivot visually and in the Static Mesh Editor. The proposed placement transform is `A R A`, translation `(x, −y, z) × 100`, with `A = diag(1, −1, 1)`. This is a candidate until you confirm the imported mesh basis. If the engine produces a different basis, stop; do not “fix” only actor yaw or only one mesh. Correct the import/transform contract consistently, then create a new sample.

## 3. Restart and verify saved assets

After shader compilation finishes, save and **fully close Unreal Editor**, reopen the project in 5.8, and reimport the Python module as in step 1. Run:

```python
report = r"C:\Art\EvergreenMarket_v3\runtime_reports\Sample_v001\IMPORT_REPORT.json"
v3.verify_after_editor_restart(report)
```

This refuses the same editor process that created the sample, loads only the generated map and writes `COLD_REOPEN_VERIFICATION.json` beside the report. A stale/edited plan, changed package, missing assets, failed checks or existing proof file stop the command. To repeat a cold check without overwriting evidence, use a fresh sample version. Material graphs still require visual/shader review; the automatic persistence checks do not prove rendered equivalence.

## 4. Manually review gameplay and appearance

**The existing BP_propChar graph is not changed.** Its E interaction is a server-side **single SphereTraceByChannel**, Visibility, radius **100 cm**, with **Start = End = ActorLocation + (0, 0, 10)**. It casts the returned Actor to StaticMeshActor, then checks the Actor's `Prop` tag or your existing whitelist.

A single trace can return the floor, wall, shelf structure or another blocking object before the desired prop. A Prop tag only filters the returned Actor; it does not search through the first blocking hit. An actor being individually tagged and having UCX collision does **not** establish trace reachability. In particular, test low objects near the floor, items behind shelf uprights, stacked copies, basket openings, a chair and a large cart/counter. A character-center sphere may also be too far from a large object's useful surface or pivot.

Use **Play From Here at a reviewed clear floor/spawn point**, or the project's existing spawn flow with its existing prop-hunt GameMode and character. The ten source spawn markers become actual **PlayerStart actors** at their authored positions and orientations. The importer does not select a GameMode, change your character or establish the project’s multiplayer startup flow. Check each PlayerStart for capsule encroachment before relying on automatic spawning.

Complete every item in `sample_review_template.json`, then copy the file to the sample report folder as `MANUAL_REVIEW.json`. It starts with every value **false**. Change an item to **true only after you actually observe it**:

- Axis probe dimensions/handedness; authored layout and pivots
- Three can copies independently selectable; no ISM/HISM representation
- Labels, wood/stone UVs, normal direction/strength, wall color, sign contact/backing, refined tree geometry, translucent glass/liquid boundaries and opaque label behavior
- No shader compile errors, missing textures or default-material fallback
- Real player capsule walking on floor and colliding with walls/fixtures without falling through; doorway/aisle clearance
- Actual E trace through server path for shelf copies, basket, chair, cart and large prop; record the hit actor at failure points
- First-hit occlusion and near-floor selection; do not solve this by globally making all floors/props PawnIgnore or QueryOnly
- After changing disguise, the mesh copied onto the character has the intended collision, capsule clearance, pivot and scale
- Both server and second client observe the selected disguise through the existing replicated/multicast path
- 67 fixture lights, no directional/sun; provisional brightness and shadows reviewed
- Ten PlayerStarts and four boundary metadata TargetPoints reviewed. Walk/attempt to leave at all four perimeter sides, corners and closed entrance; confirm the invisible barriers contain players without intruding into interior routes. Boundary enforcement comes from authored physical geometry plus four explicit invisible perimeter barriers, not from TargetPoints
- Saved/reopened map and assets remain correct
- Four invisible perimeter barriers contain players at all four sides/corners and closed entrance without blocking interior routes

If one check fails, keep it false, retain the report and stop before full import. The single-trace graph may need a separately reviewed project fix; this package does not silently change that graph.

## 5. Explicitly approve the sample

Only after the manual review and cold verification pass:

```python
checked = v3.read(r"C:\Art\EvergreenMarket_v3\runtime_reports\Sample_v001\MANUAL_REVIEW.json")
approval = v3.approve_sample(report, checked, "I reviewed the v3 sample in Unreal 5.8 and approve the full import")
print(approval)
```

This creates a new `SAMPLE_MANUAL_APPROVAL.json`, bound to the exact package/importer fingerprint, sample report hash, cold-reopen evidence and sample success token. It never sets the checklist for you. Changed package files, mismatched token, incomplete checks or altered evidence require a new sample.

## 6. Full scene, only after approval

This is a separate operation. Nothing in the sample commands calls it:

```python
full_report = v3.run(r"C:\Art\EvergreenMarket_v3", phase="full", destination="/Game/PremiumStoreV3/Full_v001", approval_file=approval["approval_file"], success_token=approval["success_token"])
print(full_report)
```

The full map is `/Game/PremiumStoreV3/Full_v001/Maps/L_V3_AllPlacements`. Expected role counts: 6,593 source StaticMeshActors, four barrier StaticMeshActors, ten PlayerStarts, four boundary metadata TargetPoints and 67 fixture lights: 6,678 role actors, with exactly 5,574 eligible source actors tagged Prop. It uses every exported placement, not the sample subset. Every eligible copy is an individual StaticMeshActor with Actor tag `Prop`; same-type actors intentionally share canonical Static Mesh assets. There is no ISM/HISM conversion. The probe is omitted from the full map. Run cold-reopen verification on the full report after another editor restart, then inspect the complete layout, full perimeter containment, all ten PlayerStarts, multiplayer and target-machine performance. Full completion reports **gameplay acceptance pending**, not “gameplay ready.”

The importer does not alter the default startup map, project package/cook list, navigation setup or shipping settings. Integrate the new full map through your normal project workflow after acceptance.

## Materials, collision and lighting policy

- Canonical FBX + named UCX only: combine meshes off, auto collision off, one convex hull per UCX, scale 1, zero import offset, scene/unit conversion on, front-X override off. The legacy FbxFactory is requested explicitly. A routing/name/property mismatch is a hard error; project-wide Interchange settings are not changed to work around it.
- UV channels stay in their exported order. An entirely UV-less, untextured source mesh may acquire a harmless blank UV0 in Unreal; that specific case is allowed and logged. Textured/source UV channels retain exact count/order checks. Lightmap UV generation is off. Every texture has its own explicit TextureCoordinate node. BaseColor is sRGB; scalar/normal textures are non-color. Normal maps require the recorded UV0 tangent basis, use NormalMap compression, flip green from OpenGL +Y to Unreal's convention, and preserve supported source strength with Normalize/Lerp. Full precision UVs are requested on the new mesh only.
- Imported source normals remain; tangents are recomputed using MikkTSpace. If actual engine cooking changes expected geometry, UVs, material slots or UCX counts, stop rather than accept a silently altered asset.
- Authored collidable props, fixtures, floor and walls use **QueryAndPhysics**, world-static object type, Pawn **Block** and Visibility **Block**. They are stationary scene actors, not simulated rigid bodies. Only explicitly nonblocking source context uses NoCollision. Collision profiles are selected and per-component responses set on new actors; global profiles are never edited.
- Closed optical materials use exact-name reviewed real-time opacity/IOR approximations. Opacity is not a physical conversion of Blender transmission. No general shader graph translation is claimed. Warm/Cold opal use exact reviewed opaque Unlit emission; the exact `EXT2_Warm_LED` signature uses Default Lit PBR plus an artistic RGB × 4 emissive term. Other emission/transmission/procedural graphs are blocked.
- All 67 fixture lights preserve the source records in the report. AREA becomes RectLight, POINT PointLight, SPOT SpotLight, with Blender local −Z emission mapped to UE local +X. Rect sizes are metres × 100. Provisional intensity is **10 lumens per source Blender watt**, attenuation radius **1000 cm**, Movable, shadow-casting. These are declared artistic starting values, not a photometric conversion or Blender look-match guarantee. Existing exposure, Lumen and renderer settings are untouched. Render-only lights/cameras and all SUN/directional lights are excluded.
- Four boundary TargetPoints retain position/orientation and labels at unit display scale. Four separate non-Prop StaticMeshActor barriers reconstruct the authored perimeter boxes using the read-only engine BasicShapes Cube, verified centred and 100 cm wide. Their actor scale uses full source dimensions in metres; source EMPTY matrix scale is half-extents and is deliberately not reused. They are QueryAndPhysics, Pawn Block, Visibility Ignore, hidden in game, component-invisible and shadowless. They span the perimeter, including the closed front entrance, and do not cover interior aisles/shelves. Source physical blockers remain. Source metadata and its original metadata-only annotations remain verbatim in the report; the separately recorded runtime boundary policy explicitly supersedes those annotations. No engine mesh is modified.

## Logs and failures

`runtime_reports/<version>/PLAN.json` records the complete plan, source data, material policies, fingerprints and manual requirements. `IMPORT_REPORT.json` records imported mesh paths/counts, before-save and after-reload checks, engine version and error details. `COLD_REOPEN_VERIFICATION.json` records the restarted-editor checks. Keep Unreal's Output Log for shader/import warnings too.

Every apply performs an exact 5.8 version check and verifies required classes, methods, enums, transient import settings and relevant editor properties before creating assets. Offline mocks cannot prove those APIs work in your installed build. Missing API/property errors should be investigated, not bypassed. An engine failure after creation begins leaves only new partial content under the named version. The script does not delete it, modify existing content, or retry into it.

## Primary API references

Official Epic documentation reviewed while writing the importer; 5.8 pages were accessible for some classes and 5.6/5.7 references were used for others. These are API references, not evidence of an engine run:

- [EditorActorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorActorSubsystem?application_version=5.8): individual actor spawn and transform APIs
- [LevelEditorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/LevelEditorSubsystem): new-level/save/load
- [MaterialEditingLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary): explicit graph creation and pins
- [Texture](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Texture?application_version=5.6): virtual-streaming setter, read-only streaming state, color/compression/green-flip properties
- [StaticMesh](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMesh?application_version=5.7) and [5.8 method index](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/genindex-G): bounds, LOD0 triangles and materials
- [StaticMeshEditorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMeshEditorSubsystem?application_version=5.6): collision counts, UV count and build settings
- [KAggregateGeom](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/KAggregateGeom): authored convex entries and extra shape arrays
- [PrimitiveComponent](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PrimitiveComponent?application_version=5.6): explicit collision-enabled/channel responses
- [RectLightComponent](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/RectLightComponent?application_version=5.7): light units, source size and intensity
- [FBX Static Mesh Pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine) and [FBX Import Options](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-import-options-reference-in-unreal-engine): UCX naming, units, normals and importer limits
