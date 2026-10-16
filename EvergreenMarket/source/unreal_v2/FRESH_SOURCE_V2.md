# Fresh import from the native v2 source

Unreal Editor execution remains unverified. Local contract, geometry, mock API and state-machine tests do not establish Unreal runtime success. Back up the project first. Nothing here edits the existing Blueprint, GameMode, pawn, existing map or existing content folder.

## Package layout

Use the complete new package, not the original handoff or normals patch. Its root contains `manifest.json`, `source_manifest.json`, `Evergreen_Market_Source_v2.blend`, `assets/`, `materials.json`, `textures/`, `walking_companions.json`, `collision_assets/`, `collision_policy_v2.json`, `neutral_light_layout_v1.json`, and these helpers in `source/unreal/`.

The native source and all render and companion FBXs are validated by SHA-256. The source-reviewed collision policy is pinned. Preparing a run copies the complete validated input into a new work folder and pins helper bytes. Each subsequent stage validates that snapshot and prior report bytes; it never searches for newest/old reports.

## Bootstrap

1. Enable the Unreal Python Editor Script Plugin and Editor Scripting Utilities if needed, then restart. Save all maps/assets. Stop Play In Editor. In the Unreal console, enter `Interchange.FeatureFlags.Import.FBX 0` to use the supported legacy FBX importer.
2. Edit only `package` and `fresh_work` at the top of `source/unreal/Start_Source_v2.py`. Use absolute paths; the work folder must not exist and must be outside the package.
3. In Unreal's Python console, run (adjust the path):

```python
exec(open(r'C:\Art\Evergreen_Market_Source_v2\source\unreal\Start_Source_v2.py', encoding='utf-8').read())
```

This only validates and prints the next stage. To prepare the new work folder:

```python
fresh_state = fw.start(package, fresh_work, execute=True)
```

Continue with the stages below in the same editor session; helper byte hashes must still match the frozen snapshot. After any later Unreal restart, rerun the exact bootstrap command. It loads the frozen helpers from `fresh_work/NativePackage/source/unreal`, checks the exact state, and performs no automatic stage. If the bootstrap finds helpers already loaded from a different folder (for example a v1 run), restart before continuing.

## Run explicit stages

```python
fw.step(fresh_state, stage='sample')  # dry run
fw.step(fresh_state, stage='sample', execute=True, backup_confirmed=True)
fw.step(fresh_state, stage='sample_lighting')  # dry run
fw.step(fresh_state, stage='sample_lighting', execute=True, backup_confirmed=True)
```

Inspect the now-lit imported sample in the editor before approving: representative fixture, carton, checkout base, paper bag and impulse display; verify outward surfaces, normals, single-sided materials, size and pivots. The sample gate does not infer visual success from a Python report. Save before continuing. Each stage leaves its new map open.

```python
fw.step(fresh_state, stage='full', visual_review_approved=True)  # dry run
fw.step(fresh_state, stage='full', execute=True, backup_confirmed=True, visual_review_approved=True)
fw.step(fresh_state, stage='collision')  # dry run
fw.step(fresh_state, stage='collision', execute=True, backup_confirmed=True)
fw.step(fresh_state, stage='pilot')  # dry run
fw.step(fresh_state, stage='pilot', execute=True, backup_confirmed=True)
fw.step(fresh_state, stage='lighting')  # dry run
fw.step(fresh_state, stage='lighting', execute=True, backup_confirmed=True)
fw.step(fresh_state)  # status and exact report paths
```

After restarting, rerun the bootstrap and open the source map named by the preceding report before executing the next stage. The full map, walking test map, four-prop pilot map and lit preview each use new generated names. No completed stage is rerun. A running/failed state blocks further mutation; keep the first error and the partial new content for inspection. Do not edit the state to bypass a failed stage.

## Collision and lighting scope

Render ISMs retain query-only selection proxies with Pawn ignored; render geometry is never blanket-enabled as walking collision. The walking stage reconstructs 694 separate hidden box components from the reviewed policy, preserving 568 existing boxes and adding 126 source-role-masked boxes. These use original scale, quaternion and translation. The 86 native companion FBXs (102 canonical boxes) are separately validated and provided for manual/native workflows; the fresh helper intentionally uses equivalent persisted BoxComponents rather than importing duplicate walking mesh assets.

Only the four existing pilot choices are promoted from ISMs to loose actors. The original Blueprint remains untouched. Lighting is a new preview-map copy using the 11-light neutral layout, unit actor scale, directional lux and point-light lumens. PlayerStart clearance is checked against every planned blocker. Actual pawn capsule, walking clearance, prop interaction, lighting/exposure and Blueprint gameplay still require Unreal review.

## Local regression tests

From a checkout with the package at `evergreen_source_v2`:

```bash
EVERGREEN_PACKAGE=evergreen_source_v2 python -m unittest discover -s source_consolidation_delivery/unreal -p 'test_*.py' -v
```
