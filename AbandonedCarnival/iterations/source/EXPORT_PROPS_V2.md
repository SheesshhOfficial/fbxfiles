# Isolated Cycle 10 gameplay prop export preparation

Prepared code only. No Blender process, scene load, export, Unreal action or validation has run for this V2 preparation. V1 files and outputs are untouched. Actual canonical counts and QA results must be measured later; V1 success is not inherited.

## Preconditions and sequence

1. Coordinator finishes visual/source review, saves iterations/Cycle_10.blend with refinement_cycle_completed=10 and approves its SHA256. Serialize every Blender invocation with renders and other scene loads.
2. Complete export_environment_v2.py first, using that same approved hash. It creates iterations/export, staged shared textures and environment/material/scene manifests.
3. Prop export requires matching environment and material manifest hashes, exact Cycle_10 path/hash, all153 eligible actors and all shared prop material slots. It refuses an existing prop manifest or nonempty prop FBX directory. Archive partial V2 prop outputs explicitly before retrying; do not erase/recreate the environment package silently.
4. Set CARNIVAL_V2_SOURCE_SHA256 for every command below. From AbandonedCarnival, run each only when scheduled:

```sh
export CARNIVAL_V2_SOURCE_SHA256=<coordinator-approved-hash>
blender -b iterations/Cycle_10.blend -t 2 --python iterations/source/export_props_v2.py
blender -b -t 2 --python iterations/source/verify_prop_fidelity_v2.py
blender -b -t 2 --python iterations/source/verify_prop_exports_v2.py
blender -b -t 2 --python iterations/source/verify_prop_texture_paths_v2.py
blender -b -t 2 --python iterations/source/verify_prop_collision_proxies_v2.py
blender -b -t 2 --python iterations/source/verify_refined_prop_collision_v2.py
```

## Isolation and unchanged behavior

All generated FBXs, manifests, import helpers and QA go to iterations/export. Texture files already staged by environment are verified by full hash and retargeted in memory. Both exporters share v2_texture_staging.py: an existing disk file is preferred; if it is missing, exact image.packed_file.data bytes are hashed with the original filepath basename. Props always use write=False, require the already-staged <hash-prefix>_<original-basename> file, and reject missing/empty packed data or any staged hash mismatch. No image encoding, duplicate texture creation or V1 material-helper overwrite occurs; prop FBXs use relative references, not embedded images. Source is never saved.

The import templates target /Game/MoonfallCarnivalV2 and retain existing material-slot assignment, imported source normals/generated tangents, query collision and Visibility blocking. Every placement remains a separate StaticMeshActor with PropActor Actor Tag; the V2 duplicate marker is MoonfallV2ImportedProp. They do not alter the user's interaction Blueprint. Unified import creates the guarded fresh V2 map through the environment helper, then props and source scene metadata. Actual engine execution and final level saving remain user/coordinator actions.

## Exact normals and canonical assets

Evaluated source normals are captured before transformation, numerically inverse-transposed, remapped after reflected winding, and written directly into FBX via the existing exact-normal payload helper. Geometry uses (100x,−100y,100z) cm; importer axis and unit conversion stays disabled. Raw source-normal fidelity is checked separately from Blender packed-normal reimport behavior. A failed reimport-normal result must be retained and explained; never silently relax it or claim runtime correctness.

Deduplication includes geometry, topology, UVs, material assignments and exact numeric source normals. Refined collision recipes contribute a separate signature so unlike collision recipes cannot accidentally share a render-only canonical key. Manifest geometry_material_uv_sha256 remains the render signature; asset_signature_sha256 additionally incorporates the recipe signature.

## Nineteen changed actors

The snapshotted prepare_refined_prop_collision_v2.py returns read-only recipes before export begins. Expected placed budget is fixed at160 hulls: seven cars ×8, eight pallets ×9 and four crates ×8. Cockpit openings, pallet fork lanes and crate central cavities remain separate from the solid proxies. Crate walls/lid/floor merge inaccessible plank seams; nails, rivets, straps, steering and other thin detail are omitted. The helper checks revision metadata, structural face ranges, convex vertex budgets, representative opening guard points and render bounds.

All other eligible props retain component-hull policies and the existing explicitly approved size-guarded small roll/hose/can/bucket simplifications. No whole-car, whole-pallet or whole-crate solid hull is allowed. These new recipes require actual overlay and engine clearance review; code preparation is not clearance approval.

## QA files under iterations/export/qa

- prop_export_report.json: source_untouched, eligible_placed_props=153, collision counts and missing/omitted collision details.
- prop_fidelity.json: all_passed covers raw geometry/topology, UVs, polygon materials and original numerical source corner normals; packed Blender encoding difference is diagnostic only.
- prop_fbx_roundtrip.json: all_passed covers independent Blender import bounds, hull counts, material-slot counts, UV presence, custom tags and normal reconstruction. Preserve any failed result.
- prop_texture_paths.json: all_passed covers resolved shared relative texture paths and zero embeds.
- prop_collision_optimization.json and prop_collision_proxy_fbx.json: current small-prop proxy policy, budgets, bounds/overlap candidates and independent exported convexity checks.
- prop_refined_collision.json: all_passed requires nineteen actors and160 placed recipe hulls; includes source recipe guards.
- prop_refined_collision_fbx.json: all_passed requires exact transformed recipe vertices/faces, closed manifold edges, independent convex volume, vertex limits, world transforms, all153 source actor identities and unchanged source hash.

Every report carries the approved source hash. Source material/UV/render fidelity, actual collision counts and total asset size remain to be measured. Unreal import, Chaos cooking, narrowphase overlap, capsule traversal, network interaction and performance are unverified.

The prop manifest records payload_origin (disk or packed_file), full payload SHA256 and staged relative path for each verified image. The environment-staged V2 material builder, including base_color_multiply_linear shader support, is reused without replacement.
