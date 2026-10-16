# Evergreen Market: walking collision and finishing checklist

## Why the character fell
The import map is a geometry/query staging map. Its meshes were set to ignore Pawn movement. Visibility-trace blocking alone does not hold up a character. The visual full import succeeding does not certify movement collision or gameplay.

## Step 1: a conservative walk-test map, without reimport
Download BOTH current files from `source/unreal/` in this repository into your extracted package's `source/` folder:
- `import_supermarket_unreal.py` (replace the older helper)
- `setup_market_collision.py`

For the path used so far, save them under `C:\Art\Evergreen_Market_Unreal_Handoff\source\`. Use GitHub's **Download raw file** button, not Save Page As. No separate Python install is needed inside Unreal.

Back up/checkpoint the project. Stop Play mode; save or discard all unsaved map/asset changes yourself. Open the original generated **Full** map matching the successful full import report. Keep Python Editor Script Plugin and Editor Scripting Utilities enabled.

In Output Log → Python, enter these lines individually:

```python
import sys, importlib
sys.path.insert(0, r"C:\Art\Evergreen_Market_Unreal_Handoff\source")
import import_supermarket_unreal as em
importlib.reload(em)
import setup_market_collision as ec
importlib.reload(ec)
package = r"C:\Art\Evergreen_Market_Unreal_Handoff"
collision_plan = ec.run(package, full_report)
```

`full_report` is the filename returned by the successful full import, not the sample report. If the editor was restarted and that variable is missing, set it to the actual successful FULL report path, for example `full_report = r"G:\Games\SheeshhPropHuntYT\Saved\EvergreenHandoff\YOUR_FULL_RUN_FOLDER\import_report.json"`. Replace the placeholder. The report must say phase `full` and status `verified_persistence` and match the current map; the helper rejects a sample/failed/mismatched report.

The command above is a dry run: it prints the planned **568 boxes** and excluded asset families, and changes nothing. After reviewing it and making your backup:

```python
collision_report = ec.run(package, full_report, execute=True, backup_confirmed=True)
```

It creates and opens a new map beside the original, named `L_Evergreen_full_WalkTest_<timestamp>`. It adds persistent, scene-owned BoxComponents, saves and reloads that copy, and verifies geometry placements plus collider count, transforms, extents and responses. It does not reimport assets, modify shared StaticMeshes/BodySetup, change project settings, or edit gameplay Blueprints. The original Full map remains intact. Reports are written under `Saved/EvergreenHandoff/Collision_<timestamp>/collision_report.json`.

If it fails, stop and share the first red Python error and collision report. A partial new copy may remain. To retry, return to the original Full map after resolving/saving/discarding changes; every run uses a new name. Do not repeatedly apply it to a collision copy. Opening the original map is the simple rollback.

## What this first collision pass covers
- Ground/site, sales and service floors, individual wall/partition segments and lintels, columns, fixed storefront glazing and overhead structure.
- Separate shelving boards, uprights, rack beams, checkout bases and freezer bodies, rather than one huge box around an aisle.
- Bakery-island base/top, produce-island base/top/legs, kitchenette base/top and staff-table top/legs, using measured subpart boxes so under-table space is retained.
- Pawn-blocking, WorldStatic, QueryOnly boxes for swept Character movement. No physics simulation. Structural boxes also block Visibility to stop selection through walls/glazing; furniture proxies ignore Visibility, leaving the original query meshes intact.
- Small products, carts, chairs and other compound props are not automatically turned into broad movement blockers.

Existing original ISM collision must still match the importer baseline; otherwise the script stops rather than mixing policies. It checks original geometry before and after the copy. It deliberately leaves the closed-looking front sliding panels/frames non-blocking until real door behavior exists. The service and yard doorway gaps are retained. No invisible perimeter is invented: you can still walk off the finite terrain at its edges. Fence boundaries, moving doors, remaining large props and tailored trace channels require a gameplay decision/pass.

**Validation limit:** local syntax and 32 contract/data/regression tests passed, including rotated/scaled centers and doorway point clearance. Epic's UE5.7 APIs were checked. This new collision helper has not run in Unreal here; UE5.8 compatibility and actual Character walking are not certified. Saved/reloaded collision checks are not a playtest. The script records `runtime_walk_test_passed: false` even when persistence passes.

## Step 2: prove walking works
1. In the new walk-test map, add/place a PlayerStart in an open aisle, with its capsule bottom above the floor and no BADsize warning. Use your existing game mode/Character. The helper does not spawn a player or change the default map.
2. The Character capsule should use object type Pawn, have query collision enabled, and block WorldStatic. A custom player object channel needs an explicit matching policy; this helper only targets Pawn. Do not enable physics simulation on a standard Character capsule.
3. Play: stand, walk, jump/land, move between sales/service rooms, through the entrance and yard doors, around checkout lanes and shelving, and under/around furniture. Test floor seams, thresholds, corners and your smallest/largest planned disguises.
4. Use viewport collision visualization/Player Collision to inspect blockers; use the real capsule sweep in Play as the deciding test. Report exact spots that block unexpectedly or remain walk-through.
5. Keep furniture-specific collision separate from prop-selection queries. No broad BlockAll operation on every object; no global complex-as-simple switch on moving physics props.

## Step 3: finish the scene in stages
- **Collision polish:** add deliberate compound hulls for remaining chairs/carts/lockers/large fixtures as required; implement door motion/collision and intentional level boundaries. Test both player movement and selection rays so shelf-wide query boxes do not hide products.
- **Player/game setup:** correct GameMode, Pawn/Character, PlayerStart, input mappings, death/respawn and intended startup map. These are project-specific and unchanged by the helper.
- **Lighting/materials:** inspect in Lit mode, establish exposure and lighting strategy, tune glass/roughness/labels. Inspect the known carton/tile tangent warnings; visual fidelity and shadow/lightmap quality need review.
- **AI/navigation, only if needed:** proxies deliberately have navigation disabled. Decide nav-relevant geometry, then configure navigation collision and NavMeshBoundsVolume and rebuild/test AI routes. Adding a NavMesh volume alone will not make these proxies export navigation.
- **Prop transformation:** build the allowed asset definitions, trace/instance-ID lookup, player visual offset, collision/camera sizing and blocked-transform checks. Imported meshes alone do not implement E-to-transform.
- **Multiplayer:** server-authoritative validation, replicated disguise state, late join, respawn and invalid-request tests. Test at least two clients before calling gameplay ready.
- **Performance/shipping:** this first pass adds 568 small proxy actors and is meant for review. Profile before combining/optimizing collision. Measure triangle/material/shadow/instance/collision cost on target hardware, choose LOD/Nanite strategy, and test a packaged build. No target frame rate is promised.

## References
- [Collision behavior](https://dev.epicgames.com/documentation/en-us/unreal-engine/collision-in-unreal-engine---overview)
- [BoxComponent extent API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/BoxComponent?application_version=5.7)
- [Level copy/load/save API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/LevelEditorSubsystem?application_version=5.7)
- [Primitive collision API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PrimitiveComponent?application_version=5.7)
- [Collision enum names](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/CollisionResponseType?application_version=5.7)
