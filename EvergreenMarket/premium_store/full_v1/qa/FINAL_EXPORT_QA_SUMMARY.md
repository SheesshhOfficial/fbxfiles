# Final offline export QA: passed

The frozen source, prepared visual derivative and final PBR derivative have a verified hash chain. All four independent final gates pass with zero errors.

- 163 canonical FBXs, 231 authored collision hulls and 6,306 independent placements
- All 5,574 eligible copies retained, across 50 eligible types
- 407 additional nonblocking visual placements, including 39 converted text objects
- 336 material slots, 138 planned engine materials and 175 planned texture imports
- 203 image files, 215 FBX texture references and all 132 baked-map review hashes checked
- 9 export-validator sensitivity tests and 30 offline material-helper tests pass
- Reported fresh-Blender round-trip vertex and UV error: zero; maximum split-normal deviation: 0.039565 degrees
- Actual PBR scene retains all 6,740 original object visibility flags, 12 collections, 13 layer collections and source light values. Its 67 area lights remain separate from the excluded preview sun.

Source SHA-256: `6ea633d3dab618fab872f6394480786ee17009e8c9921c1e3fa4f2db002a1cf1`

Prepared derivative SHA-256: `e7d59597a0afda0f622e9145d0ba4f99c528cd95c1da0ac5b0d296620086fa9a`

PBR derivative SHA-256: `76d309ec46d12092035846f3cf75be49336935fe0ea87338be35222dd77e85b9`

The source-to-prepared check found and resolved exactly 42 zero-area converted glyph triangles. The final remaining geometry, material slots, UVs and separate placement IDs pass. No opaque source item was made globally collision-permeable.

Unreal import, collision cooking, material execution, sphere-trace targeting, Character capsule behaviour, networking, performance and photometric parity remain untested. The material plan must be regenerated after relocating the package and applied in a new engine folder; actual material-slot assignment and scene placement remain engine-side work. Run the unit/axis calibration fixture before importing the complete layout.

The separate packaging audit verifies source/rebuild multipart hashes and safe existing-output behaviour, with a documented recovery note for an interrupted Python copy. Windows runtime was unavailable. Final export archive assembly/publication is separate from this certificate.
