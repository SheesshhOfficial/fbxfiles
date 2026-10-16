# Premium slice collision and export acceptance

This is a source/export checklist. No Unreal playtest has been performed by this audit. A Blender pass never establishes Unreal import, interaction, Character movement, replication, or frame-time acceptance.

## Required source invariants

- Every approved eligible placement is a distinct mesh object with a stable unique placement ID, canonical asset ID, explicit eligibility, intended `StaticMeshActor` class, and `Prop` tag. Repeated products may share mesh data; a representative-only tag or one actor per SKU fails.
- No eligible object is represented solely by a collection instance, Geometry Nodes instances, particle instances, merged shelf display, ISM, HISM, foliage or a wrapper incompatible with the Blueprint's `StaticMeshActor` cast.
- Every eligible placement uses unit positive scale. Physical dimensions live in the canonical mesh. Materials and slot order are asset-level and identical for all copies; no per-instance material override is required to reproduce the disguise.
- A canonical pivot is explicitly declared and verified. Bottom-centre is the default for this sample. A moved object origin alone is insufficient if the exported vertex positions are not in the canonical coordinate frame.
- Canonical meshes have finite, nondegenerate geometry. Check each closed connected component independently for positive signed volume, so one outward solid cannot conceal another inward solid. Intentionally open render surfaces need a recorded exception; collision hulls never do.
- Every solid eligible mesh and solid fixture has authored collision with the correct scale and alignment. Every UCX hull is closed, convex, nondegenerate and outward-facing, with positive signed volume. Render and collision objects have matching canonical transforms.
- Hull names match the exact exported render-object name: `UCX_<RenderMeshName>_<index>`. A data-block name, placement label, or almost-matching string is not sufficient.
- Compound hulls preserve basket cavities, chair leg/back spaces, cart interiors, shelf bays and fixture openings. Each hull represents a solid component; one overall convex envelope is unacceptable where its interior seals a required opening.
- Add explicit local-space empty-region probes for every required opening. Point probes are useful regression checks, but do not replace visual inspection or actual swept-shape clearance tests.
- Floor and wall blockers, boundary blockers, fixture blockers and eligible props have explicit separate collision categories. Query-only exceptions require approval; do not silently make all products query-only.

## Export and import invariants

1. Export one canonical render asset and its matching UCX objects per FBX. Keep scene placements in a manifest. Do not combine all eligible placements into a single mesh or an instanced actor during import.
2. Audit the actual FBX round trip in a fresh Blender process, preserving proof separately from the authoring source. Verify render mesh count, hull names/counts, dimensions, pivot, material-slot order, normals and positive unit scale. Round-trip success is still not an Unreal import test.
3. Record unit and axis conventions explicitly. Include an asymmetric axis probe and a known one-metre reference. Verify these in Unreal before trusting coordinates or rotations at store scale.
4. Import to a new versioned content folder/map. Match the manifest count and every stable placement ID to exactly one actor. Every eligible actor must cast to `StaticMeshActor`, carry `Prop`, reference its expected mesh asset, have unit scale, and use asset materials.
5. Inspect simple-collision body count and dimensions in the Static Mesh Editor. Preserve openings; avoid adding a full-bounds automatic hull over compound authored bodies.
6. Set the intended custom collision profile/responses in a safe order and read them back. A later named `BlockAll` assignment can overwrite deliberate query responses. Validate after saving and reloading the map.
7. Do not write an unsupported mesh replication property. Replication decisions belong to the actual actor/component/Blueprint API supported by the target Unreal version and require runtime verification.

## Existing interaction acceptance

- Reproduce the actual Blueprint: Visibility sphere radius 100 cm, centre at actor location plus 10 cm, first-hit selection, then `StaticMeshActor` cast and `Prop` tag OR mesh-whitelist eligibility. Confirm its exact start/end and single-hit/multi-hit behavior in the project rather than changing assumptions.
- Test every repeated eligible placement, including dense rows, top/bottom shelves, back rows, adjacent SKUs and items near fixtures. Count misses, fixture interception and wrong-neighbour selection; do not report a mesh/SKU sample as coverage of every placement.
- Do not turn off all fixture collision to make selection succeed. If the broad sphere cannot select reliably, report a separately approved Blueprint filtering change.
- Compare before/after dimensions, materials, pivot and orientation for the smallest can, a carton, a basket, a chair and a cart. The current Blueprint copies the mesh asset, so visual scale/overrides on the source actor must not carry required information.

## Separate Character and multiplayer gates

- Prove the moving Character root/capsule fits the disguise. An authored Static Mesh collision body does not automatically replace the Character movement capsule.
- Test walls, doors, shelf edges, corners, low clearances, steps, floor contact, spawn clearance, crouch/standing transitions, rotation and reverting the disguise. Check both visible clipping and the swept movement body.
- Verify exterior boundaries with every permitted disguise and confirm all starts remain inside the playable perimeter.
- Validate server authority and multicast consistency with ten players. Inspect actor count, collision query cost, game/render/GPU frame time, memory and shadow-light cost on the intended hardware. No benchmark or performance guarantee follows from source counts alone.

## Evidence and stopping criteria

Source QA may pass only with a machine-readable report tied to exact input file hashes, a complete eligible-placement inventory, canonical-asset inventory, collision results, and no unresolved errors. A missing manifest or source file means **not run**, not pass. Source, export round-trip, Unreal import, gameplay and multiplayer results must remain separate statuses.

## Official reference

[Epic: FBX Static Mesh Pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine) specifies matching UCX names, closed convex hulls, a per-file custom-collision limitation with multiple render meshes, and inspection of imported collision. [Epic: Simple versus Complex Collision](https://dev.epicgames.com/documentation/unreal-engine/simple-versus-complex-collision-in-unreal-engine) distinguishes simple/complex queries and the limits of Complex As Simple. Implementation details must be checked against the actual target engine version.
