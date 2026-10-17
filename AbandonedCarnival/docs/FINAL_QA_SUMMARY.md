# Final QA summary — refined Cycle 10 delivery

## Result and boundary

The export passes raw source-fidelity and collision-recipe checks. **Blender reimport normal QA is not a clean pass.** Its original failures are retained. Unreal import, shading, gameplay, multiplayer traces, Chaos cooking and runtime performance are unverified.

Frozen source SHA256: `2d4f00dbf3704895a79ea30287dfa93ac7d0ad87f6e03e0e1ea163888418ca1a`.

- 153 independently placed eligible props; 138 canonical prop FBXs.
- 43 environment tile FBXs.
- Raw source-to-FBX checks pass all 138 prop assets and all 43 environment tiles, including numerical source corner normals, UVs and material assignments; geometry meets recorded tolerances.
- Refined collision checks pass for 19 actors and 160 placed hulls, retaining actor identities, cockpit/fork-lane/cavity guards and source hash.
- Shared relative texture paths pass; prop report covers 566 references. All 41 packed images match staged texture hashes and the DejaVu font is packed. Source remains unchanged. Six supported texture Multiply tints are preserved in the material recipe; unsupported shader modulation remains explicitly approximate.

## Preserved normal-reimport caveats

Props: 136 of 138 canonical assets pass full Blender roundtrip. Two pallet assets fail only the unchanged 0.001 normal-vector-error threshold:

- `SM_wooden_pallet_244700516e`: `BY_Pallet_Low_2`.
- `SM_wooden_pallet_540b8fba44`: `BY_Pallet_Stack_4`.

Both have maximum error 0.0028084916, approximately 0.161 degrees for unit vectors. Their raw FBX normals exactly match numerical source normals. Bounds error is 0 cm; one render mesh, nine collision hulls, UV presence, two material slots and PropActorTag all pass. The existing aggregate report does not record failed-corner counts or indices. No per-corner diagnosis is claimed.

Environment: 24 of 43 tiles fail normal reconstruction, affecting 4,795 of 7,981,009 tested corners (about 0.0601%). Maximum vector error is 1.405957741 against the recorded 0.002 threshold. Raw FBX source-normal fidelity passes all 43 tiles. This larger environment discrepancy must not be represented as negligible just because relatively few corners are affected.

The measured difference arises between exact raw FBX data and Blender's reconstructed normals. Its precise internal cause and Unreal's behavior are not established by these tests. Keep imported normals enabled and inspect actual Unreal lighting/tangents before acceptance; do not silently regenerate normals, weaken thresholds or describe this as fully runtime-validated.

## Evidence

All paths below are relative to the delivered repository root:

- `export/qa/prop_fidelity.json` and `export/qa/environment_raw_fidelity.json`: raw fidelity passes.
- `export/qa/prop_fbx_roundtrip.json` and `export/qa/environment_source_roundtrip.json`: original normal failures preserved.
- `export/qa/prop_reimport_caveat.json`: quantified caveat and missing-detail boundaries.
- `export/qa/prop_refined_collision_fbx.json`: 19 actors / 160 hulls, identity and recipe geometry checks.
- `export/qa/prop_collision_proxy_fbx.json`, `export/qa/prop_collision_optimization.json`, and texture-path reports: modified small-prop and portability checks.

See COLLISION_BUDGET.md and UNREAL_ACCEPTANCE_CHECKLIST.md before engine acceptance.
