# You want it You get it — exterior refinement v2

This is a surgical visual successor to the frozen full-store v1 source. The 64 × 56 m store, interior, all 5,574 eligible prop placements, original collision library, gameplay markers, and original light objects are preserved. It is not a new full-store Unreal handoff.

## Download

Download all seven archive parts and `Reassemble_Windows.cmd` from [source_and_overlay](source_and_overlay/), keep them together, run the helper, then extract the verified ZIP. Windows PowerShell execution is not tested here. The equivalent Python helper was tested twice, including existing-output handling. The archive CRC and SHA-256 match the source package. Python users need `Reassemble.py` and `ARCHIVE_SHA256.json` alongside the parts.

## Files

- `YOU_WANT_IT_YOU_GET_IT_EXTERIOR_v2.blend`: complete Blender source derived from the v1 packed source. Includes the original interior and the refined exterior.
- `EXTERIOR_v2_HERO.png` / `EXTERIOR_v2_ENTRY.png`: Cycles exterior review views.
- `YOU_WANT_IT_YOU_GET_IT_EXTERIOR_v2_OVERLAY.glb`: isolated new exterior details and replacement tree instances, with embedded materials/textures. This does not contain the store shell, road, interior, props, or gameplay collision.
- `EXTERIOR_V2_OVERLAY_MANIFEST.json`: exact added meshes and the 61 baseline tree instance names to replace when combining the overlay with v1.
- `EXTERIOR_V2_QA.json`, `PACKED_REOPEN_QA.json`, `OVERLAY_REIMPORT_QA.json`: source-preservation, reopen, and isolated-export verification.
- `refine_exterior.py` / `verify_exterior.py`: reproducible Blender authoring and verification scripts.

## Changes

- Replaced all 61 stacked-cone tree instances with six branched conifer variants. Each has a tapering trunk, curved boughs, secondary twigs, and discrete needle sprays. Original tree transforms and stable IDs stay fixed.
- Added a honed-stone and black-metal facade treatment, warm oak vertical sign fins, raised dimensional brand lettering, storefront mullion details, and champagne-brass reveals.
- Added a deep entry canopy with oak soffit, slim posts, warm diffuser strips, exterior door handles, and a threshold.
- Added exterior benches, grasses in stone planters, bollards, paving joints, kerb and roof-edge coping. Four ground bands extend beyond the original terrain, removing the exposed slab edge from the exterior view.
- Kept original scene objects and materials unchanged except for the 61 tree mesh assignments. The old exterior sign remains intact behind a new exterior finish.

## Blender review

The original scene keeps its original world, cameras, and light objects. Choose `EXTERIOR_v2_Preview` for the dedicated daylight review setup. Its `EXT2_Exterior_Hero` and `EXT2_Entry_Detail` cameras show the refined exterior. New geometry is grouped in `12_EXTERIOR_REFINEMENT_v2`; tree replacements remain in `10_EXTERIOR`.

Images used by the source are packed. The two new base-color texture files are also supplied separately for inspection.

## Isolated overlay use

Use the complete successor blend for a coherent Blender source. When using the GLB as an additive asset, first remove or hide the 61 original cone-tree instances listed in the overlay manifest. Import the overlay once and retain its authored transforms. Do not import the overlay alongside those original tree instances without replacing them, and do not add it again on top of the successor blend.

The overlay uses standard glTF metre units with its standard Y-up conversion. A known facade width is 64.78 m at the main front coping. Check that dimension and the original store alignment in the destination application before further conversion. Source coordinates use metres and Z up.

## Verification scope

Exact geometry/transform/material-name/property hashes compare every protected pre-existing non-tree source object before and after the change, and again after reopening the successor. Tree matrices and stable IDs are checked separately. The GLB is reimported in a fresh Blender scene to check object inventory, triangle totals, and world-space bounds against the source overlay.

These are Blender checks. Unreal import, material matching in Unreal, LODs, foliage wind, light conversion, first-hit selection, player/disguise movement, multiplayer and runtime performance have not been tested. The higher-detail forest is nonplayable exterior scenery and needs target-engine LOD/performance work. The overlay adds no gameplay collision; original interior boundary collision remains authoritative. No full matched v2 FBX/Unreal package is claimed.

## Rebuild

Run Blender 4.3.2 against the frozen v1 blend with `refine_exterior.py`. The script writes only inside this versioned output folder, performs its preservation assertions, saves the new blend, exports the isolated overlay, and renders two previews. Then run the successor blend with `verify_exterior.py` to perform packed-reopen and GLB round-trip checks.
