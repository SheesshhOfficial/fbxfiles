# Collision budget — refined Cycle 10 delivery

These are exported UCX shape counts, not cooked Chaos shapes or measured physics performance.

| Scope | Canonical hulls | Placed hulls |
| --- | ---: | ---: |
| Props: 138 canonical assets / 153 independent actors | 953 | 1,049 |
| Environment: 43 tiles, each placed once | 1,323 | 1,323 |
| Combined | 2,276 | 2,372 |

Prop median is 7 hulls per canonical asset; maximum is 24. All prop assets have collision. 73 open/concave detail components are explicitly omitted; complex environment collision omissions remain listed in environment_export.json. Empty collision on decoration is intentional and is not permission to create a whole-building or whole-tile hull.

## Refined structural recipes

- Seven bumper cars × 8 = 56 placed hulls: separated hood/body/seat/undertray solids, with cockpit opening retained. Decorative fittings, steering and pickup detail are omitted.
- Eight pallets × 9 = 72: separate deck boards and stringers; fork lanes retained; nails omitted.
- Four crates × 8 = 32: four independent wall slabs, lid, floor and two skids; central cavity retained; narrow plank seams merged and cosmetic fasteners/bands omitted.
- Total: 19 actors, 160 placed hulls. Independent recipe-to-FBX checks pass. This does not establish actual capsule clearance.

## Approved small-prop simplifications

TicketRoll, CoiledAirHose, PaintCan_Open, PaintCan_Closed and OpenMaintenanceBucket use size-guarded outer proxies. Small inaccessible holes/mouths/handle gaps are deliberately filled; gameplay-useful cockpit, fork-lane and crate cavities are not.

For this refined source, the simplification changes canonical prop hulls from 1,600 to 953 and placed prop hulls from 1,740 to 1,049. Seventeen canonical meshes / eighteen actors receive these proxies. No new positive-volume actor-AABB neighbor-overlap candidates are reported. That is a broadphase bounds check, not a narrowphase intersection test.

Maximum small-prop proxy vertex count is 216; export guard is 255. Independent finite-coordinate, closed-edge, convex-volume, bounds and hash checks pass. Keep One Convex Hull Per UCX enabled and Auto Generate Collision disabled when importing the prepared FBXs.

## Acceptance still required

Do not present exported counts as cooked Chaos memory or speed measurements. Unreal import/cooking may alter hull representation. Measure cooked shape counts, scene-query cost, collision memory, player/prop movement, narrowphase contacts and multiplayer Visibility sphere traces in the actual project. Verify one eligible Actor per placement and PropActor tags. Inspect the preserved normal-reimport caveats in FINAL_QA_SUMMARY.md; raw fidelity passing does not erase those failures.

Source SHA256: `2d4f00dbf3704895a79ea30287dfa93ac7d0ad87f6e03e0e1ea163888418ca1a`. Evidence: `export/qa/prop_export_report.json`, `prop_collision_optimization.json`, `prop_refined_collision_fbx.json`, `prop_collision_proxy_fbx.json`, and `environment_export.json`. Unreal runtime and Chaos cooking remain unverified.
