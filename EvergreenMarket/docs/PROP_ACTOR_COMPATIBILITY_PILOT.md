# Four-prop compatibility pilot for BP_propChar

Blueprint supplied by you: `/Game/Core/BluePrints/BP_propChar` (project file `Content/Core/BluePrints/BP_propChar.uasset`). Its asset contents have not been inspected here.

## Why this pilot exists
Your described ChangeProp graph casts its HitActor to StaticMeshActor and then accepts an actor tagged `Prop` or a mesh in PropAllowedMesh. The original Evergreen geometry uses ordinary Actors with InstancedStaticMeshComponents, so that cast does not match its props.

This interpretation comes from your supplied behavior notes. The zoomed-out graph screenshot does not independently verify the trace/cast/OR branches. The screenshot shows **55** PropAllowedMesh entries, rather than the older 44-entry description. No Blueprint is changed by this script, and no successful E transformation is claimed until you test it.

## What changes, exactly
The script creates a NEW copy of your verified WalkTest map, retaining all **568 collision boxes**. In that copy it converts only four selected original placements into real StaticMeshActors, with the **actor** tag `Prop`:
- EM_PILOT_TomatoCan: X=-600, Y=2100, Z=0 cm
- EM_PILOT_CoffeeCan: X=-400, Y=2100, Z=0 cm
- EM_PILOT_OatsCarton: X=-200, Y=2100, Z=0 cm
- EM_PILOT_ShippingBox: X=0, Y=2100, Z=0 cm

They are deliberately relocated to the **front walkway**, whose surface is Z=0, for an accessible test row. Each corresponding old ISM placement is removed in the copy, so it is not rendered/traced twice. The complete scene still has 11,316 visual placements: **11,312 ISM instances + four StaticMeshActors**. The other 6,691 candidate placements are not converted. PlayerStart, GameMode, input, charges, mesh allowlist and Blueprints are unchanged.

The actors reference the existing canonical StaticMesh assets and embedded material assignments; no mesh duplication is needed. Selected source scales are unity within floating-point tolerance; pilot actor scales are exactly 1.0. Your reported GetStaticMesh/SetStaticMesh path does not copy component scale, material overrides, pivot offsets or collision/camera configuration. This pilot rejects source material overrides and per-instance custom data. Later non-unit-scale variants need explicit scale-aware gameplay design.

Actors are static, query-only, block Visibility, ignore Pawn movement and do not simulate physics or replicate movement. Stationary placed source props do not need individual replication merely to serve as references; the character's disguise state and server validation still need multiplayer tests.

## Run it
1. First complete the walking-collision helper and test that your character stands on the WalkTest map.
2. Back up/checkpoint the project. Stop Play and save or discard all unsaved changes yourself. Open the original successful WalkTest map, not a prior PropPilot copy.
3. Download `source/unreal/setup_prop_actor_pilot.py` using GitHub's **Download raw file** button. Save it beside the current `import_supermarket_unreal.py` and `setup_market_collision.py`, for example under `C:\Art\Evergreen_Market_Unreal_Handoff\source\`.
4. In Output Log → Python, run each line:

```python
import sys, importlib
sys.path.insert(0, r"C:\Art\Evergreen_Market_Unreal_Handoff\source")
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep
importlib.reload(ep)
package = r"C:\Art\Evergreen_Market_Unreal_Handoff"
pilot_plan = ep.run(package, full_report, collision_report)
```

`full_report` and `collision_report` must be the successful report filenames returned by those earlier helpers. After an editor restart, assign those variables to their actual files under your project's `Saved/EvergreenHandoff/` folder. A sample report or failed collision report is rejected. Do not invent the filenames or use a report from another run.

5. Review the dry-run output: exactly four promoted props, four changed groups and 568 collision boxes. It changes nothing. Then, after backup:

```python
pilot_report = ep.run(package, full_report, collision_report, execute=True, backup_confirmed=True)
```

The new map name ends with `_PropPilot_<timestamp>`. It saves/reloads and checks the remaining ISMs, four actor classes/tags/meshes/materials/transforms/collision and all walking colliders. Reports and `instance_lookup_pilot.csv` go under `Saved/EvergreenHandoff/PropPilot_<timestamp>/`.

A failed run may leave a partial COPY. Stop and share the first Python exception/report; return to the original WalkTest map before retrying. No original maps or shared assets are modified. Do not rerun the full-import/collision helper on this pilot copy.

## Test E, one thing at a time
1. Search the World Outliner for `EM_PILOT_`, select one and press F to find it. Walk the actual character close to that object; no PlayerStart is moved for you.
2. Confirm the possessed pawn is BP_propChar, IA_ChangeProp fires, and PropChangesLeft is positive. Press E once. Check whether the mesh changes and whether exactly one charge is consumed. If holding E causes repeated requests, inspect the Triggered/Started trigger behavior and cooldown; this script does not change them.
3. Watch/debug the server trace: print the returned HitActor class/name, the StaticMeshActor cast result, actor HasTag `Prop`, selected mesh and final eligibility branch. These pilot objects have the actor tag, not just a component tag. If your actual Blueprint does not accept that tag, inspect the readable graph before changing the allowlist.
4. Try both a can and a box, restore normal appearance, then check feet alignment, capsule size, camera, movement clearance, hit detection and decoy behavior. A mesh swap alone is not proof those systems are correct.

## Important: the sphere may hit the floor first
The supplied description uses a **single Visibility sphere trace, radius 100 cm, centered at actor location + Z10**. For a Character, actor location is commonly the capsule center, not its feet. For example, a center 88 cm above the floor plus 10 cm puts a radius-100 sphere into the floor. Verify your actual capsule dimensions and trace start/end; do not assume this example matches your pawn.

The floor, structural proxies or another fixture can be the first blocking hit, so the StaticMeshActor cast can still fail even beside a correctly tagged pilot prop. Tags cannot fix which object a single trace returns. **Do not disable floor/wall Visibility globally** just to make selection pass, because that removes useful occlusion checks.

If the first hit is wrong, capture a close-up of the ChangeProp trace, cast and eligibility nodes plus the runtime HitActor. A later Blueprint selection fix can gather nearby candidate props (for example an object overlap with explicit filtering, or a dedicated interaction query) and choose a valid candidate, then perform a separate line-of-sight/range check on the server. A multi trace on the same blocking Visibility channel is not automatically a solution: blocking hits can still truncate the result. Changing query channels/Blueprint logic is a separate reviewed step.

## Instance-ID and networking notes
Only affected ISM groups are rebuilt from their surviving placements. Returned indices are recorded rather than assuming removal shifts or swaps indices. Stable instance IDs remain the identity; old numeric indices in those four groups must not be reused.

The new lookup CSV explicitly includes SourceKind, ActorPath and revised ISM indices. It is an audit/export file, not an automatically cooked DataTable. If your project already uses the old lookup, update its matching struct/registry deliberately before using this pilot map. Unaffected groups retain their mappings. Materials using PerInstanceRandom may change in rebuilt groups; the supplied generated materials do not depend on it, but custom modifications require review.

The user-described reliable server/multicast calls are not a networking certification. Test server and client E requests, unauthorized targets, distance/occlusion, cooldown/charge consumption, late joining, respawn and restoration. A multicast-only appearance update may need persistent replicated state for late joiners. Do not convert all 6,695 candidates until the small pilot and performance are validated.

## Validation and limits
44 local tests passed: existing contract/collision coverage plus pilot conservation, exact four-object scope, unit scale, original-report preservation, unaffected groups, report guards and a mock ISM adapter exercising nonsequential/duplicate/invalid returned indices. Syntax passed. Relevant Epic UE5.7 APIs were checked. **This pilot has not run in Unreal here; neither UE5.8 execution nor Blueprint/gameplay behavior is claimed.** The report records `gameplay_verified: false` even after persistence succeeds.

References: [StaticMeshActor](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMeshActor?application_version=5.7), [ISM clear/add and returned indices](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InstancedStaticMeshComponent?application_version=5.7), [level copy API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/LevelEditorSubsystem?application_version=5.7).
