# Refinement-only collision recipe integration

Status: integrated into the frozen Cycle 10 V2 prop export and verified against raw FBX. All 19 refined actors retain their identities and reviewed 160-hull placed budget. See export/qa/prop_refined_collision_fbx.json. These are source/export checks; Unreal collision cooking and gameplay remain unverified.

## Entry point and side effects

New module: source/prepare_refined_prop_collision.py.

After add_bumper_realism() and add_maintenance_construction() have run in the already loaded scene, import prepare_refined_prop_collision and call prepare_collision_recipes(). This returns plain Python dictionaries; it creates no objects, changes no meshes/properties, opens/saves no file, and exports nothing. Supply objects= only when passing the complete set of seven refined cars and twelve refined maintenance props.

The return contains recipe_version, actors, actor_count, placed_hull_budget and verification-boundary flags. Each actor record has source_object, asset_family, actor_tags, source_world_matrix_blender_m, hull_count, hulls and qa. Each hull supplies vertices_local_m, triangle faces, part name, local bounds, volume and vertex count. Construction hulls also include their exact source face ranges; merged crate slabs list their constituent part names.

## Required source contract

- Exactly seven eligible BumperCar objects, sorted by name as in refine_ride_realism.py, with ride_realism_revision = cycle03_rounded_shell_seat_fittings.
- The seven headings are the ride builder's baked headings: 0.3, -0.3, 2.1, 2.8, -1.2, 0.9, -0.4 radians. Recipe vertices already contain that heading exactly once. Do not rotate by it again.
- Exactly eight BY_Pallet_* and four BY_Crate_* eligible objects with construction_refinement = maintenance_construction_v1, the original asset_family, no modifiers and complete nonoverlapping construction_components JSON face ranges.
- Run before any topology-changing modifier, mesh join or face reordering. If construction face ranges become invalid, regenerate the metadata from the maintenance builder; never infer decorative components by material alone.
- Existing object names, world transforms and PropActor eligibility must remain stable. The helper rejects missing versions, counts, ranges, unknown roles or unexpected structural labels.
- SciPy/QHull is needed only when recipes are requested. No dependency install or scene action occurs on import.

## Expected placed-hull budget

- Seven bumper cars × 8 hulls = 56. Low elliptical bumper/undertray, front hood, two independent tapered side bodies, rear body, foot tray, seat cushion and combined seat back/upholstery. Cockpit is never covered by a whole-car hull. Lamps, trim, rivets, steering/spokes, stitching, power pickup and springs are intentionally omitted.
- Eight pallets × 9 hulls = 72. Six deck boards and three stringers remain separate. Cosmetic nails are omitted. Slight plank bow/chip recesses may be convexified only within that plank; no hull joins boards or bridges the fork lanes.
- Four crates × 8 hulls = 32. Forty structural pieces are merged into four separate wall slabs, one lid slab, one floor slab and two skids. Narrow plank seams and local batten recesses are filled, while the central cavity remains empty. Nails, packing bands and buckles are omitted. No whole-crate hull is generated.
- Total for these nineteen placed actors: 160 hulls. This is a placed budget, not a claim about the eventual canonical-asset deduplication count. All other prop families keep their existing policy.

## Exporter integration, after approved validation

Use the recipe only for its matching changed source_object. Keep the evaluated render mesh path, UV/material/normal preservation, geometry deduplication and individual StaticMeshActor placement unchanged.

For each recipe's object-local point v, apply the same linear transform as the current exporter: diag(100, -100, 100) × source.matrix_world.to_3x3() × v. Correct face winding for the negative determinant. Leave actor translation in the existing placement manifest; do not bake it into hull vertices. Name each created temporary collision object UCX_<canonical_render_asset_name>_<three-digit-index> and export it with that render mesh. Delete only those temporary export objects afterward. Do not run the old disconnected-component collision path for these nineteen objects: it would add decorative fasteners back to the collision budget.

Retain one actor per placement with PropActor tag. Do not mark regeneration flags complete until the matching final FBX and QA are verified. Do not apply these recipes to the old V1 bumper/crate/pallet geometry.

## Validation to schedule between renders

The helper rejects proxies over 255 vertices, invalid source face ranges, blocked representative cockpit/fork-lane/cavity guard points and AABB extensions beyond a 5 mm tolerance. These are geometric guards, not final acceptance.

Run it once in the approved loaded refined scene, with before/after object counts, identities, meshes, transforms, tags and source hashes checked for mutation. Inspect every bumper heading in collision overlays, especially hood/side slopes and the open cockpit. Inspect all pallet fork lanes and crate wall/lid/floor contact heights. Verify source-local/world bounds, hull convexity, intersections at joining slabs, UV/material/corner-normal fidelity, FBX roundtrip and cooked collision naming/counts after export. Log any intentionally omitted thin geometry.

No Blender scene test, overlay render, FBX export, Unreal import, Chaos cooking, capsule clearance, multiplayer trace or performance result is claimed by this preparation deliverable.
