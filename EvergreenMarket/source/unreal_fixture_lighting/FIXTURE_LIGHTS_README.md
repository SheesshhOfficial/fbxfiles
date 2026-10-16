# Evergreen fixture point-light patch

This is a lighting-only patch for the user's already working native source-v2 final Preview map. It does not rebuild/import the store, replace its meshes, modify collisions/props, or change GameMode, E interaction, exposure or materials. Keep the source-v2 package and C:\Art\Evergreen_Native_Run_01 unchanged.

## Quick steps in Unreal

1. Extract this patch folder to `C:\Art\Evergreen_Fixture_Lighting`. Keep `Start_Fixture_Lights.py`, `fixture_point_patch.py`, and `fixture_point_layout_v1.json` together. If choosing another folder, change `fixture_folder` near the top of Start_Fixture_Lights.py. The existing state defaults to `C:\Art\Evergreen_Native_Run_01\run_state.json`; do not edit its contents.
2. Stop PIE. Save all current map/content edits and back up the project. Open the completed source-v2 final Preview map that has working collision and E interaction, not a sample map. If an older package's helpers were loaded in this Unreal session, restart Unreal before this step.
3. In Unreal's Python console run the following (safe preflight only):

   `exec(open(r'C:\Art\Evergreen_Fixture_Lighting\Start_Fixture_Lights.py', encoding='utf-8').read())`

   Alternatively, use Tools > Execute Python Script on Start_Fixture_Lights.py. Inspect the printed dry run: exact source map, 11 generated lights to replace and their current settings, 42 proposed point lights, actor snapshots, and any unrelated manual directional lights that will be preserved. A wrong map, changed helper/state/report, missing old generated light, unknown generated identity, or dirty editor stops the operation.
4. After a successful dry run and backup, explicitly execute:

   `fixture_patch.run(fixture_state, fixture_layout, execute=True, backup_confirmed=True)`

   This creates and loads a NEW uniquely named `_FixtureLights_...` map next to the existing final Preview map. It removes only that copy's 11 tagged generated preview lights (including the generated Sun), leaves the PlayerStart and manual/unrelated lights intact, and creates the 42 fixture points. The original saved map is untouched.
5. The script saves and reloads the new map, checks fixture transforms/settings, 694 collision boxes, four promoted props, existing ISM geometry, and preserved actor identities/labels/tags/transforms plus stable manual light settings. The result report is under the project's `Saved/EvergreenHandoff/FixtureLights_.../fixture_lights_report.json`. Look for `verified_fixture_lights_persistence`. Review Lit view and test walking/E in the new map; runtime appearance/gameplay have not been tested here.

## Restart and recovery

After a restart, run step 3 again to restore the Python variables; do not paste only the execute line in a fresh session. The current map guard rejects a patched or partial copy. Do not rerun against that copy. If execution fails, stop and inspect the failure report/partial map before changing anything. The script never discards dirty changes or edits run_state.json/report hashes to bypass a failure. Return to the original saved Preview map only after consciously saving or resolving any current edits. Re-running from that original makes a separate map copy, never duplicate lights in one existing map.

## Source-driven layout and tuning

- 25 ceiling/aisle points: 3000 lumens, 900 cm attenuation radius, just below the real LED diffusers; includes the rear warehouse row.
- 15 canopy points: 250 lumens, 500 cm radius, just below their fixtures.
- 2 exterior wall points: 1000 lumens, 600 cm radius, outside the lamp face.
- The 15 fridge LED strips remain emissive accents.

All new lights are white, temperature disabled, movable, inverse-square point lights, explicit unit scale, shadow casting enabled, source radius 2 cm. No directional, sky, rect or arbitrary fill-grid lights are created. Any manual directional light is preserved and warned about; remove it manually if unwanted. These are initial settings, not a calibrated lighting design. Forty-two movable shadow-casting lights may need performance tuning in the target engine. Custom layout JSON may adjust intensity/radius and small fixture-relative offsets; provenance and one-per-fixture coverage remain checked.

## Verification scope

Local tests exercise source layout coverage, changed layout settings, exact removal scope, tuned old preview lights, copied-map path remapping, incorrect/current map guards, dirty-state rejection, state/report/helper integrity, duplicate prevention, unit-scale correction from factory scale 2.5, preserved actor snapshots and manual light setting drift. They are not Unreal integration tests. Non-light snapshot checks all actors' membership/class/path/label/tags/world transform; the frozen source-v2 verifier additionally checks ISM scene geometry/materials/transforms, collision and four promoted props. This is not a serialization-byte comparison of every possible custom Blueprint variable. Manual light snapshots compare stable settings, excluding transient IDs/ticks/delegates.

Official Unreal 5.7 API references used:
- https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorActorSubsystem?application_version=5.7
- https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PointLightComponent?application_version=5.7

The patch uses documented destroy_actor/set_actor_transform boolean returns and point source-shape setters; it reuses the frozen verified source-v2 helpers without modification.
