# Premium grocery store: approval-stage proposal

Status: layout proposal only. Single floor, Evergreen Market name, fictional realistic brands and the premium departments are confirmed; this floor plan and visual blockout still require approval. No changes to the existing Evergreen project, no finished build, and no performance guarantee.

## Recommended footprint

64 × 56 m interior envelope (3,584 m²), about 70% larger than the previous 44 × 48 m envelope. This compares envelope area, not walkable floor area. Approximately 64 × 44 m is customer space; the rear 12 m band holds connected stock/staff areas. Ten players. A larger store needs playtesting to avoid long searches; keep the first layout compact enough to learn.

Warm oak/walnut shelving accents, cream stone/tile, dark metal framing, restrained brass details and coherent packaging families. Warm fixtures above actual aisles and counters, with neutral enough product lighting for readable labels. Forest and road are a backdrop, not another gameplay zone.

## Department arrangement

Coordinates are metres from the front-left inside corner, +X right, +Y toward the rear. Blocks are reserved department areas, not final collision walls.

- Front band, Y0–10: entry vestibule, checkout islands, customer service and basket/trolley parking. Main entrance near X40–48. Checkouts must leave an unmistakable bypass route.
- Front-left, X0–12/Y0–16: coffee/patisserie seating. Chairs, movable tables and eligible service items are real transformable placements. Keep seating out of entry and checkout flows.
- Left-middle, X0–12/Y16–32: produce and premium fresh foods, low islands and varied silhouettes.
- Rear-left customer side, X0–12/Y32–40: bakery with bread wall and preparation backdrop.
- Front-right, X52–64/Y0–12: florist and seasonal gifts, leading into beverages/wine at Y12–24.
- Rear-right, X52–64/Y24–40: deli/cheese and butcher/seafood counters. Clearly divide their visual identities; operational prep areas connect to the rear staff route.
- Middle, X16–48/Y14–36: pantry, snacks, cereal, household and personal-care aisles. Two banks separated by a 4 m cross-aisle at Y24–28; do not create uninterrupted long shelving corridors.
- Rear customer band, X16–48/Y36–40: dairy/chilled/frozen. Leave walk-through connections to the rear loop; refrigerated units never form a continuous blocking wall.
- Rear loop, Y40–44: visible circulation connecting the sales floor, bakery and deli, with at least two separate staff access points.
- Staff/stock band, Y44–56: shared circulation spine at Y44–47, connected receiving/warehouse and cold storage on the left/centre, staff office/break area, toilets and utilities on the right. Reserve customer toilets with access from the rear shopping loop and staff toilets with access from the service spine; door clearance and internal partitions are a greybox-stage requirement. Looped routes, no compulsory one-way dead ends. Cold-room doors and loading doors need explicit boundary rules.

## Circulation and gameplay targets

Main loop and cross-aisles: 3.5–4 m clear. Secondary shopping aisles: initially 2.4–2.8 m clear. Staff connectors: initially 1.8–2.4 m clear. These are gameplay targets, not building-code certification. Clear means after shelf lips, carts, chairs, displays and collision hulls are placed.

Use two central shelf banks rather than one deep maze. Keep regular cross-connections, recognisable department landmarks, and alternate routes between front, centre and rear. Low produce islands and glass-front counters provide partial visibility; shelves and walls provide meaningful cover without hiding entire wings from navigation. Avoid excessive decorative clutter on the traversable floor.

Outside scenery is visual only. Exits receive explicitly named, visible-in-editor blocking volumes aligned to the intended boundary; they must not cut through interior aisles or affect the interaction channel unnecessarily. Use believable closed exterior doors/glazing where practical. Test that neither player nor permitted disguise can escape, and no player starts outside the playable perimeter.

## Blender-to-Unreal contract

1. One versioned master Blender file with named collections for structure, fixtures, eligible props, authored collision, lights, exterior scenery and gameplay markers. Every placement has a stable ID and explicit eligibility/collision category.
2. Every placement of every approved product, box, basket, bin, cart, chair and large movable object exports as an individual StaticMeshActor tagged Prop. Mesh data/material assets are shared across copies; placement actors are not combined into ISMs. No per-SKU representative-only conversion. Structural and ineligible decorative objects may be instanced.
3. Eligible assets use canonical applied scale, deliberate pivots and asset-level material assignments. This matters because the existing Blueprint copies the mesh asset, not arbitrary source instance scale/material overrides. Every eligible mesh must have a tested disguise profile, especially large carts/chairs.
4. Each solid eligible asset carries appropriate simple collision in its FBX: simple convex shapes for cans/cartons, compound convex pieces for baskets/chairs/carts where empty space matters. Fixtures use authored compound hulls with openings preserved; floors/walls have clean simple bodies. Tiny thin details do not get oversized blockers. Query-only/decorative exceptions are explicit and approved, not silently applied to all products.
5. World placement collision and transformed-character collision are separate acceptance checks. Stationary solid props should physically block appropriately; eligibility does not imply physics simulation. The Character root/capsule or an approved alternative must fit each disguise during movement. Blender hulls alone cannot prove that the Blueprint's moving character will collide correctly.
6. Preserve the existing tag-based eligibility flow, but validate its actual 100 cm Visibility sphere and first-hit selection in realistic shelf arrangements. A dense shelf can return an unrelated fixture or neighbouring item. Do not disable all fixture collision to force interaction. If selection cannot be reliable, propose a separately approved Blueprint filtering change.
7. Light positions, types, orientation and physical units are authored metadata derived from visible fixtures. Import explicit lumens, radius, scale and shadow policy; no accidental default intensity or directional-light substitution. Colour/exposure/shadow quality is validated in Unreal, not promised from the Blender preview.
8. Import into a new versioned content folder and map. No old-map deletion. Generate reports covering every placement ID, asset, actor, eligibility tag, collision hull count, material slots, world transform and light identity. Reload the saved map and re-verify.

## Performance safeguards without reducing eligibility

All eligible placements stay individual actors. Use shared static mesh/material assets, reusable packaging atlases, appropriate LODs/Nanite where supported, sane texture resolution and no unnecessary ticking, simulation, overlaps or actor replication. Do not claim high graphics settings remove CPU/collision or network cost. The existing server/multicast interaction must be profiled with ten players.

Count eligible actors, unique meshes/materials, collision hulls, texture memory and shadow-casting lights before dressing the whole store. Establish a representative fully stocked aisle benchmark early. Measure game-thread, render-thread and GPU time, memory, trace behaviour and multiplayer consistency on the user's actual hardware. If targets fail, adjust artwork/layout/light implementation together while retaining every approved eligible placement, or ask for an explicit scope decision.

## Approval and verification stages

A. Approve floor plan, one-floor choice, name/fictional branding, departments and eligible categories.
B. Greybox: ten-player routes, doorway clearances, stockroom loops, starts and exterior boundaries; no premium dressing yet.
C. Representative aisle plus produce/counter samples: actual packaging quality, materials, fixture-based lighting and all copies eligible. Test movement and transformation with the smallest can, medium box, chair and cart before mass replication.
D. Full Blender authoring and exports: automated inventory/count, outward-normal, scale/pivot, collision-hull and placement-uniqueness checks.
E. Fresh Unreal import: save/reload validation, all eligible placement tags and mesh assets present, no duplicate visuals, doors/aisles clear, no falling through floors.
F. Ten-player network/performance playtest, then polish and delivery. Offline script tests do not substitute for Unreal gameplay checks.

Decision still pending: approval of this proposed footprint, layout and blockout views. Actual hardware and FPS target are still useful despite the user's high-end graphics preference.
