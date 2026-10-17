# Independent final v3 source QA

PASS after glyph-contact correction. Source reopened from disk and compared independently with exterior v2.

- 5,574 eligible placement objects retained with unchanged transform, mesh, custom properties, and material assignments.
- 231 collision-library objects and 14 gameplay markers unchanged.
- Six physical glass display counter instances unchanged.
- Every original EXT2 object unchanged. No baseline object missing. No undeclared changes.
- 58 ceiling hangers contact actual board-top and roof-underside triangles.
- 58 ceiling anchor plates overlap roof surfaces and hanger geometry.
- All five wall plaques have actual header contact at all nine sampled face positions. COLD STORE, STAFF OFFICE, and BREAK ROOM embed 3 mm; CUSTOMER WC embeds 8 mm; STAFF WC embeds 18 mm.
- All four refrigerator plaques contact actual case fascia at fixing height. The plates overhang narrow fascia vertically. FRESH DRINKS spans two adjacent case headers and their central seam; its left/right fixings contact the cases.
- Exterior wordmark carrier contains all 2,514 sampled glyph rear vertices and bridges to their actual rearward facade triangle hits.
- All 38 interior glyph sets physically overlap their backing faces by approximately 0.300 mm, verified from evaluated text meshes.
- All 75 source file images are packed, including both 1024 by 1024 floor textures: base color sRGB, normal Non-Color.

Scope: Blender source geometry, placement data, mounting contacts, and packed-texture verification. This does not certify structural engineering, Unreal runtime behavior, glTF parity, or visual appearance in every renderer. Material assignment fingerprints do not constitute a full shader-graph comparison.

Detailed evidence: FINAL_INDEPENDENT_QA.json. Reproducible audit: audit_final.py. Baseline world-space font bounds: baseline_mounts.json.

Audited source SHA256: c4abf30a478051c30e00536642416c53fefb7db4911128dbb8114c0732975519
