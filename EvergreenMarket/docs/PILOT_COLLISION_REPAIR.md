# Finish verification of the four existing pilot props

The diagnostic showed the pilot StaticMeshActors still used the named BlockAll preset: QueryAndPhysics, Visibility Block and Pawn Block. The intended policy is Custom, QueryOnly, Visibility Block, Pawn Ignore. E transformation can work while this movement-collision policy is wrong. The previous failed report was therefore correctly rejected by the normals helper.

The updated pilot helper selects Custom explicitly and applies collision after editor-property updates. This repair does not rerun conversion or rebuild any instances. It copies your currently saved working failed-recovery map and changes collision on only the four existing tagged pilot actors in that copy. Original maps, meshes, Blueprint, manual lights/PlayerStart, and all 568 walking proxies remain in place. It does not edit the old failed report.

## Run the scoped repair

1. Back up your Unreal project, stop Play and SAVE all current map/content changes. Keep your working recovered map open, the one with four visible props and working E.
2. Extract `Evergreen_Pilot_Collision_Repair.zip`. Copy all Python files from its `source` folder into `C:\Art\Evergreen_Market_Unreal_Handoff\source`, replacing the older helper copies.
3. In Output Log → Python, run the read-only preflight:

```python
exec(open(r"C:\Art\Evergreen_Market_Unreal_Handoff\source\Start_Pilot_Collision_Repair.py", encoding="utf-8").read())
```

This restores variables after an editor restart and finds the unique failed report for the CURRENT map. It checks all meshes, transforms, remaining ISM placements and walking proxies while identifying the four collision settings to repair. Missing or changed scene data stops the run.

4. After reviewing the four-actor plan and confirming the backup/save:

```python
pilot_collision_report = er.run_current(package, execute=True, backup_confirmed=True)
```

The new map ends in `_CollisionVerified_<timestamp>`. The helper requires all collision, scene, material, tag, transform, actor snapshot and proxy checks to pass before AND after saving/reloading. Only then does it write a new successful `prop_pilot_report.json`. A failure remains a failed report and separate partial map; stop and send the first exception. Do not edit a status field or bypass a check.

## Continue the normals repair

Keep this newly verified map open. Your existing normals patch data stays at `C:\Art\Evergreen_Market_Normals_Patch`. Run:

```python
exec(open(r"C:\Art\Evergreen_Market_Unreal_Handoff\source\Start_Normals_Repair.py", encoding="utf-8").read())
```

Then follow the normals guide's sample command, visual check, and full-stage instructions. The new successful report will now match the map exactly. Return to this CollisionVerified map before the full normals stage, not the failed older recovery map.

Install this helper update AFTER copying helpers from the older normals ZIP, so older packaged helper copies do not replace the fix. The original normals geometry ZIP is unchanged.

## Validation limits

Local tests model named-profile reset behavior and verify the copying/report/guard logic. They do not run Unreal. The repair's actual save/reload verification and your walking/E tests are still required. Official component API: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PrimitiveComponent?application_version=5.7
