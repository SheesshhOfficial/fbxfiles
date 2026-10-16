# Source checkpoint v2

This is a versioned derivation of the original logical-mesh Blender handoff. The originals were not overwritten. It is a fixed, verified source checkpoint, not an unrestricted mesh-editing/export pipeline.

## Verified content

- 256 linked render meshes, 534,154 vertices and 887,528 triangles across the unique assets; 11,316 original placements.
- 246 consistently oriented, closed negative-volume shells corrected, reversing 45,192 triangles. Open shells and near-zero cases were not blindly flipped.
- Original vertex coordinates, triangle membership, material slots/face assignments, smoothing flags and vertex-to-UV associations preserved exactly.
- All original scene object transforms preserved exactly after save/reopen.
- The 256 render FBXs match the previously validated corrected payloads byte-for-byte: 178 corrected assets and 78 unaffected assets.
- 111 original query collision boxes remain in their render FBXs. The 145 original `none` entries retain that legacy query-body meaning.
- Walking collision is a separate set of 86 actual companion FBXs, containing 102 outward-facing UBX boxes. The explicit instance masks place 694 boxes, preserving the earlier 568 and adding 126 for reviewed physical fixtures.
- All 31 newly covered asset bounds and custom proxy containment passed a 0.01 cm tolerance; maximum discrepancy was 0.000331725 cm. Fence rails remain separate thin rails; bollard body and reflective band were verified coaxial and overlapping.
- All 342 FBXs passed exact collision Model-name/Geometry-connection checks. The original query Geometry nodes may be named `Collision`; their connected Model nodes have the required `UBX_...` names.
- 31 original Blender lights retained. Eleven typed `UE_LIGHT_...` empties store neutral Unreal light positions/settings. These are metadata markers, not a watts/lumens conversion.

## Authoritative normals

The `EG_ExportNormal` float-vector corner attribute stores the exact corrected export normals. Its maximum error against the validated FBX normals is zero.

Blender 4.3 stores its display split normals in a compressed representation. In this model, reconstruction around pre-existing degenerate bevel fans differs by more than 0.002 vector units on 3,267 of 2,662,584 corners. Some adjacent nondegenerate faces share these fans. The largest display-normal vector discrepancy is approximately 1.0. This limitation affects Blender's decoded display normals, not the exact export attribute or delivered FBX normals. An ordinary stock FBX export can reintroduce this loss.

Use the delivered guarded snapshot exporter. It checks every native mesh, exact corner normal and placement against the approved checkpoint before emitting the validated render payloads. It exports the native walking UBX prototypes separately. Vertex, UV, normal and placement mutation regression tests all confirm rejection. Edited geometry requires a deliberate re-baseline and new normal validation; stale attributes are never treated as a valid new export.

## Running the portable snapshot exporter

From the package folder, with Blender on the command path:

```
blender -b Evergreen_Market_Source_v2.blend --python source/blender/export_source_snapshot.py -- . NEW_EXPORT_FOLDER
```

The destination must not exist. The exporter needs only this package and Blender's bundled FBX codec. It does not require the earlier original handoff or winding patch package. The exported folder contains the import contract, FBXs, textures, collision policy and light layout; retain this source package as the native source checkpoint.

The construction/provenance scripts are included separately. `consolidate_native.py` requires the named original handoff, validated winding patch and reviewed policy inputs; it is not the portable re-export entrypoint. Earlier procedural authoring scripts may retain authoring-workspace paths and are provenance, not a one-command rebuild promise.

## Runtime boundary

Blender and FBX cannot fix an Unreal Character capsule, movement component, disguise transform, Blueprint collision profile or dynamic overlap handling. Walking bodies must be imported as separate hidden companion components/actors using their instance masks and explicit collision responses. Do not combine query and walking hulls into the same simple body, and do not spawn companions on every placement without respecting the masks.

No Unreal runtime test was executed in this environment. The delivered fresh-import helper has its own dry-run and sample-first validation path.
