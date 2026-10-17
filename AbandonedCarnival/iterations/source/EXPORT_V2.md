# Isolated Cycle 10 environment export preparation

Status: Cycle 10 V2 environment export and all three validators have run against frozen SHA256 `2d4f00dbf3704895a79ea30287dfa93ac7d0ad87f6e03e0e1ea163888418ca1a`. Current output has 43 tiles, 6,042 environment source objects, 1,323 UCX hulls and 3,135,875 triangles. Raw source geometry/topology/UV/material/normal fidelity passes all 43; relative texture paths resolve. Blender reimport overall remains failed: 24 tiles have 4,795 mismatched corners, with maximum normal reconstruction angle 89.332981 degrees. Refer to current QA for full diagnostics; do not claim full normal roundtrip or Unreal validation. V1 remains unchanged. Later packed-image and generalized-tint code preparation tests are separately labeled below.

## Coordinator sequence

1. Finish visual reviews, save `iterations/Cycle_10.blend` with scene property `refinement_cycle_completed=10`, run final source QA, freeze its SHA256.
2. Serialize with rendering. Set `CARNIVAL_V2_SOURCE_SHA256` to that approved hash, then from AbandonedCarnival run:

```sh
export CARNIVAL_V2_SOURCE_SHA256=<approved-sha256>
blender -b iterations/Cycle_10.blend -t 2 --python iterations/source/export_environment_v2.py
blender -b iterations/Cycle_10.blend -t 2 --python iterations/source/verify_environment_raw_fidelity_v2.py
blender -b iterations/Cycle_10.blend -t 2 --python iterations/source/verify_environment_source_roundtrip_v2.py
python iterations/source/verify_environment_texture_paths_v2.py
```

3. All generated assets, manifests, copied textures, import helpers and QA go under `iterations/export/`. A nonempty output directory is refused; archive a partial or prior V2 attempt explicitly before retrying. No source save operation is present.
4. Integrate the separate prop exporter into this same output package only after environment export finishes. It must use the same Cycle 10 source SHA and coordinates, and source material-slot mapping. Environment exporter refuses a prepopulated destination. It does not copy V1 prop FBXs, manifests or unified importer. Coordinator must adapt the V2 prop importer to `/Game/MoonfallCarnivalV2` and share the prepared materials.
5. Evaluate raw fidelity and Blender roundtrip separately. Preserve failed normal reconstruction results; V1 had exact raw source normals but Blender packed-normal reimport discrepancies. V2 requires fresh measured results and an explicit caveat report if needed. Do not inherit V1 success/counts.

## Geometry and collision integration

The exporter is a separate snapshot of the V1 environment exporter, with the same exact raw numerical normal payload correction (`source/fbx_exact_normals.py`). It retains evaluated geometry, per-corner UV/material data, transformed source normals and reflected winding. Coordinates remain `(100x,-100y,100z)` cm; importer conversions disabled; normals imported, tangents generated.

It excludes eligible PropActorTag objects, assembly sources, render-only objects, visual replacements, render-hidden, viewport-hidden and locally hidden objects. New stalls and roof replacements therefore do not duplicate the hidden originals. Gameplay ride-car geometry remains the prop exporter's responsibility.

`decorative_no_collision`, `decoration_only` and the funhouse facade `collision_policy` are honored before primitive collision selection. Existing foliage/grass/leaf/trim exclusions remain. Cycle 6 groundmarks and aggregate, Cycle 8 growth and Cycle 9 story dressing must remain visual-only. Unsupported complex carousel/funhouse meshes are reported as omitted collision rather than convex-hulled across openings.

The two known `Cycle01 caravan ... formed barrel roof` meshes receive twelve independent roof-only convex sheet strips each. The source topology is checked (196 vertices, 194 polygons, no modifiers); a changed layout fails pending review. Each strip spans four of the 48 authored samples and retains 35 mm sheet thickness. The report includes maximum sampled chord deviation. This is an approximation requiring Unreal collision cooking and roof traversal review. No body/interior/door/window volume is enclosed. Existing trailer walls keep independent primitive collision; no entire trailer hull is generated.

New stall counter boards retain simple primitive UCX; scalloped valances and flashing are decorative. Existing simplistic collision coverage limitations persist and are listed per source.

## Materials, lights, isolation

Referenced image files are copied into the isolated output `textures/` directory with content-hash-prefixed names, then only the in-memory image paths are retargeted. When the original disk file is unavailable, exact image.packed_file bytes are staged with the original basename and the same SHA256-prefix rule. No pixel re-encoding, unpack operation or source save occurs. Missing or empty disk/packed data fail; mismatched existing staged files fail without overwrite. FBX uses relative paths without texture embedding; material manifest references this output texture directory.

The existing material/scene metadata extractors are reused without modifying their V1 files. New practical light placements/colors/source energies are extracted from the loaded Cycle 10 source. Blender render-only effects remain excluded. Unreal photometric translation and glass/foliage shader approximations require engine review.

Prepared environment/material/metadata import helpers are copied on export with `/Game/MoonfallCarnivalV2` destinations. The target level remains a new, guarded level; existing assets/dirty maps are refused. No map deletion or automatic final save. Unreal execution, collision, navigation, normal/tangent shading, material appearance and gameplay remain unverified.

## Cycle 6 asphalt tint compatibility

V2 uses `export_material_manifest_v2.py` and the `import_materials_v2.py` template. The asphalt patch's direct sRGB image → MixRGB MULTIPLY (factor 1, unclamped, constant tint) is represented by `base_color_multiply_linear` and an explicit Unreal Multiply expression after texture decoding. This preserves the linear shader calculation without an 8-bit rebake or an incorrect sRGB-space tint. The source graph is checked during export; unsupported graph changes or missing textures fail instead of silently dropping tint. Only this recognized graph's stale approximation warning is removed.

`qa/environment_material_compatibility.json` now records the actual source hash, extracted tints, wetground roughness and the constant-color damp-margin/tar/rubber values from the loaded final source. These values are not hardcoded to override later reviewed source changes. The new puddle roughness should read 0.19 from Cycle 6; shader appearance still needs engine review.

Preparation test `test_v2_material_tint.py` passed extraction, five unsupported-graph rejection cases, actual importer-branch wiring with API doubles, and linear multiply algebra. This is not Blender execution, a source-value audit or Unreal shader validation. See `iterations/qa/v2_material_tint_preparation.json`.

## Packed-image portability code update

`v2_texture_staging.py` provides the shared environment/prop byte-selection and staged-path logic. Existing disk files remain preferred; packed bytes are read lazily only when the disk path is unavailable. Environment may create staged files; props perform hash-verified read-only lookup. Future environment reports include per-image payload origin, full hash and staged relative path.

This is a post-export preparation change. The current V2 export used resolved disk files and was not regenerated or modified by this update. Pure temporary-file tests passed (`iterations/qa/v2_texture_staging_preparation.json`); actual Blender packed-image fallback remains to be exercised. The helper-copy namespace replacement was also narrowed to `/Game/MoonfallCarnival/` so an already-V2 template is not double-suffixed. Existing generated helpers were not changed by this code update.

## Completed save-free material refresh after export

The V2 extractor now recognizes every supported direct sRGB Image Color → MixRGB MULTIPLY (constant factor 1, clamp off, unlinked RGB tint) → Principled Base Color graph, including matching Forest leaf materials. Asphalt support remains mandatory. Unsupported modulation retains the original approximation warnings and is listed separately in compatibility QA; no generic graph is guessed to be equivalent.

The coordinator completed this refresh successfully on the frozen source. To reproduce after checking the same approved source/export hashes, run from AbandonedCarnival, with no concurrent source edits:

```sh
export CARNIVAL_V2_SOURCE_SHA256=2d4f00dbf3704895a79ea30287dfa93ac7d0ad87f6e03e0e1ea163888418ca1a
blender -b iterations/Cycle_10.blend -t 2 --python iterations/source/refresh_material_manifest_v2.py
```

The refresh checks the caller-loaded source path and approved/source-manifest hashes, resolves textures through the shared exact-byte helper with `write=False`, and repaths only in memory. It writes only `iterations/export/unreal/material_manifest.json` and `iterations/export/qa/environment_material_compatibility.json`, plus `iterations/export/qa/source_portability.json`. Portability QA checks the expected 41 image count, exact packed-byte SHA256 against staged files, packed fonts/builtin font availability, and unchanged source SHA256. Existing staged textures are required; missing/mismatched textures fail without creating files. No FBXs, import helpers, source scene, or V1 files are written. A new source version requires a newly approved hash and matching exports, not reuse of this command's hash.

### Verified refresh outcome

The completed refresh reports 6 supported multiply materials: Arena burnished steel wear, Arena dark aged oil on scanned metal, Cycle06 asphalt patch aggregate, Forest leaf • deep green, Forest leaf • sage light, Forest leaf • warm olive. The earlier four-tint mock test covered four fixtures; it was not the final source material count. All 41 packed image SHA256 values match their existing staged texture bytes; DejaVu Serif Bold is packed, and builtin fonts are available. Source SHA256 remains unchanged. These are source/byte checks, not an Unreal rendering test.

`iterations/export/qa/environment_reimport_caveat.json` summarizes the final measured normal discrepancy: 4,795 of 7,981,009 corners across 24 tiles exceed the unchanged 0.002 vector tolerance (about 0.114592 degrees); maximum angle is 89.332981 degrees. It lists every affected tile and source-component attribution. Raw FBX normals and UVs are exact, topology/material assignment is exact, and all Blender non-normal bounds/UV/material/triangle/corner/hull checks pass within recorded tolerances. Unreal normals/tangents and shading inspection remains required. The report can be regenerated without Blender using `python iterations/source/summarize_environment_caveat_v2.py`.
