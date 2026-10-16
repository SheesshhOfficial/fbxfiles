# Evergreen source collision and lighting policy v1

## Scope and verified counts

This is source metadata and an exporter mapping plan. It does not change the user's Unreal map, Blueprints, character capsule, or imported assets.

- 256 canonical render assets; 11,316 original placements.
- 111 legacy single-box collision assets cover 10,217 placements. 145 assets with no source collision cover 1,099 placements.
- 51 disguise candidate assets cover 6,695 placements. All already have a legacy UBX query box. Those boxes are conservative selection proxies; accurate shape-fitting has not been certified.
- 568 reviewed walking boxes reduce to 66 canonical-local boxes belonging to 55 assets. The generator checks forward transformation and inverse recovery for every original walking box, with placement scale and quaternion rotation preserved.
- Every asset has an explicit strategy, reason, export action, runtime query policy, and companion-body policy in collision_policy_v1.json. asset_policy_audit.csv is a flat review index.

## Critical separation of bodies

Unreal imports all UBX/UCX shapes belonging to one render asset into one aggregate simple body. Individual hulls in that body cannot carry independent Pawn/Visibility responses. Never append the walking proxies to a render asset while trying to keep its old box query-only.

1. Render asset body: retain existing legacy UBX where present, Custom / QueryOnly, Pawn Ignore, Visibility Block, all other responses Ignore. No collision where the original asset has none.
2. Walking companion body: separate component or separately exported companion static mesh, with the listed local boxes. Custom / QueryOnly, Pawn Block. Visibility Block for structural pieces only, Visibility Ignore for fixtures. No simulation.
3. Provenance geometry is excluded from exports. Source collections and typed prototype meshes must not accidentally appear as rendered store fixtures.

Companion names are deterministic: original SM_EG_<suffix> becomes SM_EG_Walk_<suffix>. Its boxes use UBX_SM_EG_Walk_<suffix>_00, _01, etc. If exporting FBX companion bodies, provide an intentional hidden carrier mesh and validate the resulting body setup. Exporting collision-only FBX objects without a matching mesh is not an established import path. Existing independent BoxComponent placement is the validated planning baseline.

## Mapping and clearances

Local box centres/full sizes are centimetres, in Unreal axes, relative to the canonical bottom-centre pivot. Blender local metres are [x/100, -y/100, z/100]. Apply placement scale, then quaternion rotation, then translation. Half-size is used only when constructing BoxComponent extents. Do not bake scale twice. Duplicate display names are not keys: use exact canonical asset_id and instance_id.

The canonical reduction is valid only because all matching original placements reconstruct the reviewed boxes. A world collider is not generally reusable as local mesh collision. Modified geometry or different placements require rerunning mapping tests and bounds checks.

- Architecture stays segmented at door gaps and lintels.
- Sliding entrance glass, door frame and visibility strip are explicit nonblocking doorway exceptions.
- Bakery, produce island, staff table and kitchenette use subpart boxes; signs and empty spaces under the table are excluded.
- Fences are not promoted to a bounding rectangle. Boundary collision needs spans and approved gate openings; wire/post geometry alone does not establish a navigational perimeter.
- Existing no-collision scenery remains explicitly nonblocking. This is not proof every omitted solid fixture is gameplay-complete. Audit entrance planters, bollards, impulse display body, chilled case body, rooftop units and boundary spans before extending the walking allowlist.

## Accurate prop hull work still required

Retain the 51 legacy candidate query proxies until replacements have passed geometry QA. Cartons can use tight fitted UBX. Cans, bottles, fruit and loaves should use low-complexity convex hulls derived from the corrected render geometry. Stems and small protrusions need a deliberate gameplay tolerance, documented per asset. Open carts, baskets, pallets, chairs, mug handles, crates, bins and compound appliances need convex subparts that preserve meaningful gaps. A single convex hull over the whole object can close openings and is not automatically acceptable.

This deliverable does not label those future hulls generated or tested. Shape-tightness is false in the policy for every candidate until measured. Pawn-body/capsule resizing and the E transformation logic remain a separate gameplay task.

## Export acceptance gate

Before replacing any known-good FBX or enabling newly generated hulls:

- Export into a new versioned folder, keeping the corrected baseline FBXs and original source unchanged.
- Compare asset IDs, instance IDs, pivots, local bounds, material slot order, all vertex positions, triangle connectivity, UV corner association, split normals and smoothing against the corrected baseline. Count changes need a justified collision-only exception.
- Check closed render and collision shells have outward winding; preserve intentionally open surfaces.
- Reimport to a temporary QA scene; verify mesh/UV/material data, units, scale and winding. A Blender-only roundtrip is insufficient evidence of Unreal import success.
- Verify Unreal body shapes, per-component Custom responses, save/reload persistence, collision trace hit ownership, door/table gaps and all original 568 companion placements. Do not silently activate complex-as-simple or BlockAll.
- Test walking with the actual player capsule and prop transform character. A collider-fitting test does not establish capsule clearance.

## Neutral inspection lights

neutral_light_layout_v1.json specifies 11 typed lights: one directional Sun at 10,000 lux, nine interior point lights at 12,000 lumens and one pilot fill at 6,000 lumens. Locations and attenuation radii are centimetres; orientation is Unreal pitch/yaw/roll degrees; all scales are explicitly one. Point lights use inverse-square falloff and no shadows, Sun casts shadows, all are movable and neutral white.

Store these as metadata/typed empties in Blender, alongside original authored lights. Do not equate Unreal lumens/lux with Blender watt energy. Blender orientation conversion needs a tested adapter for light forward axes; metadata remains authoritative. PlayerStart is not part of this layout. These are inspection lights, not production art lighting.
