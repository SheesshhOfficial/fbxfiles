# You want it You get it — independent source QA

Result: **PASS_AUTHORED_SOURCE_ONLY**. All six final source gates pass with zero errors. The main source geometry report also has zero warnings.

Frozen master SHA-256: `6ea633d3dab618fab872f6394480786ee17009e8c9921c1e3fa4f2db002a1cf1`

## Verified counts

- 5,574 eligible placements across 50 eligible types. Every copy has its own mesh object, stable ID, unit scale, canonical asset materials and `StaticMeshActor` import intent with `Prop` tag.
- 5,899 total physical placements; 116 canonical assets and 231 valid named convex hulls, expanded to 9,530 placed hulls.
- 1,473 outward closed render shells, 404 classified intentional open surfaces, 425 outward image-printed front faces, no degenerate triangles or inward closed shells.
- 37 source-clear routes, 11 internal doorways and ten supported, clear player-start markers.
- Exact 3,584 m² playable-floor support, eight low/standing boundary checks and ten render/collision roof/facade coverage checks.
- All 144 central shelf copies and 4,320 central product copies face their aisles.
- All 330 cold-stock front paths are clear in actual render and collision geometry. All 30 deli/meat/fish items have clear open-back staff approaches; their customer glass remains intact.
- Minimum measured staff-side body clearance: 0.579998 m for the 0.45 m source probe. The thirty chosen product-centre distances are at most 0.887484 m across the stated actor-height assumptions.
- Zero guaranteed vertical misses at assumed actor-origin heights 0.90, 0.96, 1.00 and 1.10 m, using the unchanged +0.10 m offset and 1 m sphere radius.
- 67 actual fixture-aligned area lights; one separate render-only sun excluded from the default gameplay lighting list. Presentation cameras are explicitly excluded.
- 71 packed texture images. Source materials, light transforms/values and inventory agree with the manifest.

## Limits that still matter

These are authored-source checks. No Unreal import, Visibility query-response readback, single-hit target selection, disguise, Character capsule, network or performance test has run here. Clear paths and vertical overlap do not prove reliable selection in dense stock. Deli items are approached from the staff side. Lighting energy remains in Blender units; Unreal photometry is unvalidated.

FBX/PBR derivative checks belong to the separate export reports. The source cannot repair the Character root capsule or guarantee multiplayer authority.

## Evidence

`FINAL_SOURCE_QA.json` binds all six detailed reports to this exact master hash. `CHECKPOINT_REPORT_INDEX.json` preserves five review passes and the pass-five access refinement, including real failures and their measured fixes. Validator scripts and 29 synthetic regression checks are retained for reruns.

The corrected full-store assets supersede the old frozen slice for front-print orientation: a later supplemental check found two backward image-label planes in the slice; both are corrected here. The old slice was preserved unchanged.
