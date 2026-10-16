# Evergreen controlled 16-prop expansion

Offline-prepared addon. No Unreal or PIE run is claimed. No Blueprint changes.
Place the runtime files in `C:\Art\Evergreen_Prop_Batch`.

Required runtime files: `Start_Prop_Batch.py`, `prop_batch_patch.py`, `fixture_support.py`, `prop_batch_selection_v1.json`.
Existing source-v2 helpers stay in their original run-state location and are SHA-256 checked before import. The copied fixture support is isolated; no original scripts are modified. Close/restart Unreal if a different source helper module is already loaded.

Save all current changes and open the exact successful FixtureLights map. The default run-state is `C:\Art\Evergreen_Native_Run_01\run_state.json`. The exact fixture report is `G:\Games\SheeshhPropHuntYT\Saved\EvergreenHandoff\FixtureLights_20261016_203347_2abafb60\fixture_lights_report.json`. No newest/latest-file search is used.

1. Unreal Python console, preflight only:

`exec(open(r"C:\Art\Evergreen_Prop_Batch\Start_Prop_Batch.py").read())`

2. After reviewing the summary and backing up the saved project:

`prop_batch.run(str(prop_batch_folder), execute=True, backup_confirmed=True)`

After an editor restart, run command 1 again before command 2. Both calls independently validate the exact state, reports, helper hashes, selection hash, source scene, original four props, 694 collision boxes, the exact approved 31 fixture-light identities, and clean editor. Dry-run never copies/saves the map.

Execution copies to a short unique `L_EG_PropBatch_<timestamp>_<suffix>` map in the same Maps folder. Only 16 selected original ISM placements become StaticMeshActors at their exact original full world transforms using existing shared mesh assets. Descending per-component instance removals are followed by explicit transform-to-stable-ID survivor remapping, handling shift and swap engine orderings. Ambiguous duplicate transforms in affected groups stop preflight. Every remaining instance is verified; only selected instances are removed.

Expected result: 11,296 ISM instances + 4 original pilot actors + 16 new Prop actors = 11,316 original logical placements. New props use the proven Custom / QueryOnly / Visibility Block / Pawn Ignore profile, physics and replication disabled. The user intentionally removed 11 canopy points after the successful 42-light patch. The retained set is exactly Fixture_01–Fixture_25, Canopy_01/07/12/15 and ExteriorWall_01/02. The historical 42-light success report remains unchanged as provenance. This addon never restores removed lights; restored removed keys, unknown keys, duplicate keys, wrong source identities or missing retained lights stop the run. Existing manual actors, current saved light tuning, mesh/material/component settings, four pilot props and collision boxes are compared across copy, before save, and after reload. Saved user lighting adjustments are preserved rather than forced back to published brightness.

Full report and all-source lookup CSV are written to `Saved\EvergreenHandoff\PropBatch_<timestamp>_<suffix>`. A failed run writes `failed_partial_prop_batch`; stop and share that report. Never rerun a partial map, edit reports, or discard changes automatically. No failure-recovery mutation is included.

The 14 low endcap products and two stockroom cartons need manual E interaction / disguise-fit testing. Existing shelf/pallet blockers can occlude traces. This does not prove BP compatibility, multiplayer behavior, or reachability. Selection JSON includes per-item geometric caveats.

New API checked against Epic's official Python API:
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InstancedStaticMeshComponent?application_version=5.7
`remove_instance(instance_index)` returns bool; the code does not assume stable survivor ordering.

## Find and test the batch

Filter World Outliner for `EM_BATCH_`, select one actor and press F to focus. The label includes its mesh type and stable source ID. `PROP_BATCH_SELECTION_AUDIT.md` lists all 16 world positions. In PIE, approach from the adjoining aisle and test E once on a bottle, can, carton and stockroom box, then test the other selections. Existing Blueprint screenshots show a 100 cm-radius Visibility sphere at ActorLocation + (0, 0, 10), not an eye-height ray. A shelf, pallet, floor or neighboring original ISM can become the first hit; if a selection fails, capture the hit actor/component before changing anything. Check disguise scale/pivot, walking past shelves and doors, then a two-player server/client test. Respawn/reset the normal charge allowance between tests if needed.

The 21 local unit tests (including 8 selection audits) passed. These use offline data/mocks; actual Unreal save/reload and gameplay validation happen when this addon is run.

## Updating after the 42-light preflight stop

Download this updated ZIP and replace its files in `C:\Art\Evergreen_Prop_Batch`. Save All in the same current map containing your approved 31 lights. Run command 1 again to load a fresh isolated addon module; no editor restart is needed solely for this addon update. It must report 31 preserved fixture lights and 16 selected props. Only then run command 2. The previous count guard stopped before any map copy or prop edits.
