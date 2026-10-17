# You want it You get it — premium interior refinement v3

Open `YOU_WANT_IT_YOU_GET_IT_REFINED_v3.blend`. This is the complete packed Blender store, including the refined v2 exterior, all 5,574 eligible placements, and the original gameplay/collision layout. It supersedes the v2 source for visual review; historical versions remain untouched.

## Download

Download every file in `source_and_overlay` into one folder. On Windows run `Reassemble_Windows.cmd`; on other systems run `python Reassemble.py`. These reconstruct and checksum-verify the ZIP; then extract it and open the `.blend`. The Windows helper was inspected but not executed on a Windows runtime. Preview PNGs are published separately in `previews` beside this package.

## What changed

- All 38 interior sign texts now sit on real colored backing plates. The 29 suspended assemblies have twin rigid charcoal ceiling hangers, roof-contact plates and brass clamps. Five room plaques are attached to actual wall headers; four small refrigerated-case plaques attach to the case fascia.
- The sixteen aisle labels are larger and legible, with forest-green boards and warm cream raised lettering. Department boards use restrained terracotta, sage, deep green and muted teal, with slim brass rules.
- Walls use mineral sage, deep forest, terracotta and clay instead of uniform white. Existing warm oak and charcoal metal are retained.
- The floor is warm greige honed stone with packed base-color and tangent-normal textures, explicit repeating UVs, satin roughness and contrasting flush grout. Its geometry and continuous collider are unchanged.
- A discreet charcoal carrier now physically joins the retained v2 exterior wordmark to its oak facade backing. No existing exterior geometry was changed.
- Original physical counter glass, all existing meat/fish stock and open staff-side access are preserved. The user confirmed the original glazing is visible in rendered view; material-preview reflections are not treated as solid slab geometry.

## Review files

`BEFORE_*` and `AFTER_*` PNGs are actual Blender Cycles camera renders. The corresponding pair uses identical camera and lighting settings. Rendering scripts are included. The supplied preview passes can retain visible Monte Carlo grain; the packed source remains suitable for higher-sample renders.

`REFINEMENT_MANIFEST.json` lists every changed original, every addition and each sign's supports. `qa/FINAL_INDEPENDENT_QA.json` and `qa/FINAL_QA_SUMMARY.md` record independent source and actual-triangle contact checks. `OVERLAY_ROUNDTRIP_QA.json` checks isolated export inventory and geometry in a fresh Blender import.

## Portable isolated overlay

`REFINEMENT_v3_OVERLAY.glb` contains ONLY the v3 replacements and additions, not the full store. Its new stone material uses standard UV image textures and normal mapping; new paint/metal materials use standard PBR values. Fonts are converted to meshes and zero-area faces cleaned only in the export session. Source text stays editable.

Use the complete `.blend` whenever possible. To combine this overlay with the complete exterior v2 source/export, first remove or hide every original name listed in `changed_objects` in `REFINEMENT_MANIFEST.json`, then import this overlay once. Keep all other original objects. Do not import it on top of the complete v3 source or leave the old white floor/walls/text/boards visible underneath replacements. Do not duplicate the v2 exterior overlay when starting from the complete v2/v3 source.

Coordinates are metres, source Z-up; glTF applies its standard Y-up mapping. The floor remains exactly 64 × 56 m. No new gameplay collision is included; existing original colliders remain authoritative. Added signage is above the player navigation envelope or attached to existing surfaces.

## Verification boundaries

The 5,574 eligible copies remain individual objects with their original transforms, mesh geometry, material assignments and custom properties. All 231 collision-library objects, 14 gameplay markers and six glass display counter instances are unchanged. Original exterior v2 objects are unchanged. Physical support contacts are tested against evaluated geometry, not just parent links or bounding boxes.

This is a complete revised Blender source plus an isolated visual overlay. The historical v1 FBX/baked-material handoff has NOT been regenerated. No full matched v3 Unreal package, Unreal import/material parity, character clearance/disguise fit, first-hit traces, multiplayer or performance test is claimed.

## Reproduce from exterior v2

Use Blender 4.3.2 and run these in order:

1. Open the complete `premium_store_exterior_v2/YOU_WANT_IT_YOU_GET_IT_EXTERIOR_v2.blend`; run `build_refinement.py` from this version folder.
2. Open the resulting `YOU_WANT_IT_YOU_GET_IT_REFINED_v3.blend`; run `finalize_refinement.py` once. This applies QA-driven plaque and exterior-carrier corrections and calibrated floor pixels.
3. Run `export_overlay.py` on that saved source. It performs conversion/export and fresh-import geometry verification without resaving the source.
4. Run the review scripts against the baseline or final source as documented by their command-line arguments. They render without saving either source.

The packed final `.blend` needs no scripts or external images to open. The two new texture PNGs are also supplied separately. Rebuilding from scratch requires the preserved complete exterior v2 baseline, not only its isolated overlay. Do not run the additive finalization twice on one file.
