# Fresh corrected Evergreen import

This route starts from the original handoff plus the validated normals patch. It uses no old import, collision or pilot reports. It keeps both source packages unchanged and prepares a new local package containing all 256 meshes, with the 178 patched FBXs substituted and their manifest hashes updated.

The helpers create new Unreal maps/assets. They do not restore deleted content or modify your Blueprints. Source Blender lights are not imported; inspect the sample with suitable Unreal lighting. Runtime editor execution still needs validation in your project.

## Before starting
- Back up the project, save your blank/current map, and stop Play.
- Install the entire current helper set together in C:\Art\Evergreen_Market_Unreal_Handoff\source. Do not mix earlier helpers. This set explicitly uses Custom collision profiles for generated components and four pilot actors.
- Original package: C:\Art\Evergreen_Market_Unreal_Handoff
- Normals patch: C:\Art\Evergreen_Market_Normals_Patch, with patch_manifest.json directly inside.
- Work folder: C:\Art\Evergreen_Fresh_Run. It must not exist for a new run. Existing work is never overwritten. To start a distinct new run, choose another unused folder in the starter rather than deleting prior work.
- Enable Python Editor Script Plugin and Editor Scripting Utilities, then restart Unreal if requested. In the Unreal console, use Interchange.FeatureFlags.Import.FBX 0 so the validated legacy FBX options apply.

## 1. Preflight
In Output Log → Python:

```python
exec(open(r"C:\Art\Evergreen_Market_Unreal_Handoff\source\Start_Fresh_Market.py", encoding="utf-8").read())
```

This only validates inputs or reads the exact existing state file. It does not import anything.

## 2. Prepare the new local corrected package

```python
fresh_state = fw.start(package, patch, fresh_work, execute=True)
```

This copies data into CorrectedPackage and records the exact state path. No Unreal import occurs yet. Keep this folder and run_state.json intact. Helpers are snapshotted with hashes to make restarts reproducible.

## 3. Import a corrected sample

```python
fw.step(fresh_state, stage="sample", execute=True, backup_confirmed=True)
```

The sample includes the importer's required representative meshes plus the shipping carton, checkout base, paper shopping bag and impulse display. For neutral sample lighting, while that exact sample map is open:

```python
fw.light_sample(fresh_state, execute=True, backup_confirmed=True)
```

In the Outliner, search PaperShoppingBag, Checkout_base, Impulse_display or ShippingCarton_Floor; select a matching actor and press F to focus it. Sample assets retain their original store positions, so omitted shelves/supports can make isolated objects appear to float. Then inspect Lit and Unlit from several sides. Verify solid outward surfaces, labels/materials, dimensions and placement. Save any edits before proceeding. Walking collision and the E-enabled four-actor pilot are later stages; they are not expected in the sample.

## 4. Build the full map, walking collision and four pilot props
After the sample looks correct, leave that exact sample map open, save the project, then:

```python
fw.finish(fresh_state, execute=True, backup_confirmed=True, visual_review_approved=True)
```

This performs Full import → walking-collision copy → four-prop pilot copy, checkpointing the exact successful report after each stage. It keeps the Custom collision profile, verifies persistence after reloading each stage and does not bypass the sample gate. Do not interrupt the editor while a stage runs.

Alternatively run one stage at a time with fw.step(fresh_state, stage="full", execute=True, backup_confirmed=True, visual_review_approved=True), then stage="collision", then stage="pilot". Leave each stage's resulting map open for the next stage.

For an optional final preview copy with neutral lighting and a checked PlayerStart:

```python
fw.preview(fresh_state, execute=True, backup_confirmed=True)
```

The final map still needs your gameplay configuration and E transformation checks. No Blueprint is edited, and the new mesh assets may require review if your Blueprint uses an explicit mesh whitelist.

## Restart or check status
Rerun Start_Fresh_Market.py after restarting Unreal. It reads only C:\Art\Evergreen_Fresh_Run\run_state.json and loads that run's snapshotted helpers; it never selects the latest report. fw.step(fresh_state) prints the completed stages and exact reports. A completed run is read-only when finish is called again.

If you prepared the package in the same editor session, the original helper modules remain valid while their bytes match the snapshot. After a restart, the starter loads the copied helpers. If it reports a mixed helper folder, restart Unreal before retrying.

If a stage fails or is interrupted, stop and retain the first exception, the printed report path and run_state.json. A partial new map may remain. The wrapper deliberately blocks automatic retries and state editing because a stage may already have created assets. Do not delete source files, rewrite the state, or substitute an old report. Report the failure for a scoped recovery or use a separately named fresh run after review.

## Preview and gameplay limits
The optional preview supplies one movable directional light and ten movable point lights; it is a neutral inspection setup, not final production lighting. The new PlayerStart is at (-300, 2280, 103) cm, facing toward the pilot row. Its conservative 50 cm radius / 100 cm half-height envelope clears all 568 planned blockers, but your actual pawn capsule and GameMode spawn selection still require a Play test. Select your existing Prop Hunt GameMode in World Settings if it is not already the project default. No GameMode or Blueprint is guessed or modified.

Exactly four props become individually traceable StaticMeshActors tagged Prop: TomatoCan, CoffeeCan, OatsCarton and ShippingBox. The remaining scene uses instancing; this does not make all 6,695 candidate placements compatible with a StaticMeshActor-only Blueprint. Deleting prior content may invalidate mesh whitelist references, so test E again with these new assets.

Material creation now explicitly sets and verifies the contract blend mode and two-sided flag, including Opaque, after saving/reloading. No blanket two-sided fix is used. API reference: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Material?application_version=5.7 .
