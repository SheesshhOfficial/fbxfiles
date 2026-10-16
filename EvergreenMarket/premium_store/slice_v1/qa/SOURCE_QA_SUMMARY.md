# Premium pantry slice: independent source QA

Result: **PASS_SOURCE_ONLY**. 0 errors; 0 unresolved warnings.

This is a Blender-source and manifest result. No FBX round trip, Unreal import, Character movement, interaction, multiplayer or performance test has been run.

## Verified source coverage

- 488 distinct eligible placements across 11 eligible assets: 487 packaged products and one shopping basket. Every eligible copy has a unique matching source/manifest ID, unit local/world scale, shared canonical mesh data, asset-level materials, intended StaticMeshActor class and Prop tag.
- Six separately placed shelf bays and eight physical-context placements: floor slab, ceiling, end wall, dado, two side walls, console base and stone top.
- 20 canonical assets and 42 authored collision hulls. All hulls have exact matching canonical names, closed convex geometry, consistent outward winding and positive volume. All collision object transforms are identity.
- 243 unique closed render shells are outward; zero negative closed shells. 170 deliberately open printed-label/side-lettering shells are explicitly classified. 16 decorative meshes were also checked after evaluating modifiers.
- All 210 context records are classified. The 202 intentional nonblocking objects have reasons: lettering, flush grout, thin attached trim, overhead/integrated lighting and camera-only captions. Zero unclassified render objects.
- 13 independent basket-cavity/handle and shelf-bay point probes remain clear. Nine source-space foundation probes fall inside the authored continuous floor slab. These are regression checks, not swept-character clearance tests.
- Carton side lettering fits all four physical side panels. Canonical pivots are deliberate; product bottom-centre checks allow a reported 2 mm or 0.5% dimension tolerance for small rims/print details.
- All 10 source packaging textures are packed. Source files were not modified by this audit.

## Eligible placement counts

- almond_granola: 48
- bronze_pasta: 49
- chickpeas: 48
- coffee: 65
- crushed_tomatoes: 33
- olive_oil: 49
- rolled_oats: 49
- sea_salt: 48
- shopping_basket: 1
- strawberry_preserve: 49
- wildflower_honey: 49

## Resource counts, not benchmarks

- 547 eligible-placement collision hulls after expansion; 72 shelf hulls and eight physical-context hulls.
- 1,773,604 eligible-placement triangles after expansion; linked assets share mesh data. These counts do not establish frame time or network cost.
- 35 authored Blender light records. Watt values are source metadata, not verified Unreal lumen conversions.

## Required downstream checks

1. Export one canonical render asset and its matched UCX hull set per FBX; verify an asymmetric unit/axis probe, dimensions, material slots and normals after export/import.
2. Spawn every eligible placement as its own StaticMeshActor with Prop, preserve unit scale and asset materials, save/reload and reconcile every ID.
3. Read back final collision profiles/responses. Do not overwrite a deliberate query profile with a later BlockAll assignment. Do not use an unsupported mesh replication property.
4. Test the actual 100 cm Visibility sphere at ActorLocation plus 10 cm against every crowded-shelf placement. A source pass does not prove first-hit selection.
5. Separately verify the Character root/capsule for each permitted disguise, walls, floor, shelves, doors and clearance. Authored mesh collision does not automatically repair the moving Character capsule.
6. Run ten-player server/client and frame-time tests on the intended hardware.

## Evidence

Source: `EVERGREEN_PANTRY_VERTICAL_SLICE_v1.blend`
Source SHA-256: `fb52a3daa3e403a9853d37d1350b67989bfc18b1d495a54c7623bc8562707a60`
Manifest SHA-256: `18524eb8104c2af6957e1f6d049f36404d8f043d59c9076422f7c15ec42575e4`
Geometry/placement fingerprint: `e9a140d3d0ca5021fb06432e0058911a23197c42654ba6887e08753b570bb7ad`

Machine-readable result: SOURCE_AUDIT_FINAL.json. Validator: audit_blender_slice.py. Eleven synthetic validator tests pass, including inward shells, concavity, open labels and hidden-object transforms.

Official pipeline guidance: [Epic FBX Static Mesh Pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine).
