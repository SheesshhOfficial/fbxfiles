# Native source and repeatable export

The master file is Evergreen_Market_Source_v2.blend. It contains the corrected render meshes, original linked scene placements, visible named collision collections and Unreal light-position/settings markers. The original 31 Blender lights are retained. The Unreal layout uses 11 explicitly typed lights and is a neutral starting point, not identical photometric rendering across engines.

## Validate or export with Blender 4.3.2

From a terminal with Blender available (replace executable/package/output paths as needed):

```text
blender -b "C:\Art\Evergreen_Market_Source_v2\Evergreen_Market_Source_v2.blend" --python "C:\Art\Evergreen_Market_Source_v2\source\blender\export_source_snapshot.py" -- "C:\Art\Evergreen_Market_Source_v2"
```

To produce a new render/collision export, append a nonexistent output folder:

```text
blender -b "C:\Art\Evergreen_Market_Source_v2\Evergreen_Market_Source_v2.blend" --python "C:\Art\Evergreen_Market_Source_v2\source\blender\export_source_snapshot.py" -- "C:\Art\Evergreen_Market_Source_v2" "C:\Art\Evergreen_Source_Export_02"
```

The exporter verifies all native meshes, exact corner-normal attributes, UV/material associations, source placements and collision proxies before emitting the approved render FBX payloads and regenerating collision companion FBXs. The output contains render/collision assets and metadata; retain this complete master package for the fresh starter, which also validates the native .blend and helpers.

## Important source limitations

The exporter deliberately preserves exact approved FBX payloads after proving that they match the native source. It is a guarded reproducible snapshot exporter, not a general-purpose exporter for edited geometry. Editing geometry, normals, UVs, materials, placement transforms or collision definitions requires a reviewed new baseline. It will refuse stale data rather than silently export old geometry.

Blender's compressed custom-normal display representation differs slightly from the exact corner-normal attribute at some pre-existing degenerate bevel fans. The exact attribute and emitted FBX normals are independently validated; the viewport's reconstructed normals are not the export authority. Local QA reports record this limitation.

The procedural build/polish scripts are included for provenance. Do not rerun legacy build scripts over the master package. The outward-box/UBX variants document the generator fixes; any newly regenerated scene still requires the full geometry and export validation process.

## Collision exports

111 render FBXs, including all 51 candidate prop types, contain their own simple UBX hulls. 86 separate companion FBXs contain 102 canonical walking boxes, instanced under the reviewed masks to 694 world boxes. Their visible carrier geometry exists for the FBX import convention and must not be rendered as duplicate surfaces.

The included Unreal workflow validates these companions but creates equivalent hidden BoxComponents from the same source policy, rather than importing duplicate walking mesh assets. A physical render-only fixture dragged into an unrelated map alone does not automatically gain its companion. Apply the corresponding companion/policy or use the included workflow.

A hull on a StaticMesh asset does not choose the component's collision profile or change a Character capsule. Runtime profile/transform behavior still belongs to Unreal.
