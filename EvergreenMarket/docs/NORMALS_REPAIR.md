# Evergreen closed-shell winding repair

## Confirmed cause
The original procedural cube helper ordered all six faces inward. FBX roundtrip inspection confirms inward closed shells in 138 of the 256 render meshes (246 closed shells), including ShippingCarton_Floor, checkout cuboids and floor slabs. Cans and many other meshes are already outward. Cardboard, paper, tape and ink are opaque; changing their blend mode or enabling Two Sided globally does not correct the topology.

This patch reverses only inward **closed** shells and their corresponding split normals. It retains vertex positions, UV associations, material slots, pivots and outward/open shells. Collision-box winding is repaired separately. See the generated geometry audit for exact coverage and roundtrip validation. Open or degenerate shells are not automatically classified as outward/inward and remain unchanged.

## Preserve the working project
Back up the project and save your current successful recovered pilot map, including manual lights, PlayerStart and any other edits. Stop Play. Do not reimport the entire old handoff, overwrite the existing mesh assets, rebuild collision, or rerun the prop conversion.

The Unreal helper creates a new map from your saved current map and imports corrected sibling StaticMeshes into a new folder. It switches only matching generated mesh references in that copy; the original map and mesh assets are unchanged. All other actors and instance transforms are checked against a before/after snapshot. Walking proxies remain in place.

The existing Blueprint is untouched. Pilot actors retain their Prop actor tag and class. Their GetStaticMesh result becomes the corrected sibling asset in the patched copy. An eligibility path based only on an explicit old mesh whitelist will not automatically include new assets; test E again. Do not bulk-edit the whitelist without reviewing the actual Blueprint. Rollback is simply opening your saved original map.

## Stage the repair
1. Apply the sample to the shipping carton and checkout base first.
2. In the new sample map inspect both Lit and Unlit from several sides. Confirm the box is solid, labels and materials are unchanged, the checkout looks correct, walking still works, and E transformation still works with the box.
3. Only after that visual/gameplay check, apply the full affected set from the original successful pilot map. Do not stack a full patch on a sample copy.
4. Inspect the full result under your actual lighting. Geometry validation is not certification of lighting, reflections, texture quality, multiplayer, or all gameplay.

The source fix and Blender/FBX checks are local tests. Unreal execution is not available in the delivery environment; the editor helper has not been runtime-tested here. If a run fails, retain the first exception and generated report, and stop. A partial new copy may remain; do not delete your original map or bypass validation.

## Windows commands

Extract the patch ZIP to `C:\Art\Evergreen_Market_Normals_Patch` so that `patch_manifest.json` is directly inside that folder. Copy the five `.py` helpers from the extracted patch’s `source/unreal/` directory into `C:\Art\Evergreen_Market_Unreal_Handoff\source`.

Open your successful recovered pilot map with the working E transformation. In Output Log → Python:

```python
exec(open(r"C:\Art\Evergreen_Market_Unreal_Handoff\source\Start_Normals_Repair.py", encoding="utf-8").read())
```

After backup, saving all changes and reviewing the dry run:

```python
normals_sample_report = en.run_current(package, patch, execute=True, backup_confirmed=True)
```

After the sample passes your visual/gameplay checks, return to your saved original recovered pilot map. Full plan:

```python
normals_full_plan = en.run_current(package, patch, phase="full", sample_report=normals_sample_report, visual_review_approved=True)
```

Then execute the full patch:

```python
normals_full_report = en.run_current(package, patch, phase="full", execute=True, backup_confirmed=True, sample_report=normals_sample_report, visual_review_approved=True)
```

If you restart Unreal between these steps, rerun the starter and set `normals_sample_report` to the actual successful sample report filename printed by the helper. Do not choose a failed report or a sample from a different source map/patch version. Keep the generated normals report: older import/pilot reports still describe the original mesh paths, not the patched sibling assets.

## Delivery verification

Final FBXs are edited using Blender’s official FBX parser/writer, directly preserving original data rather than Blender mesh re-export. Exact payload checks and Blender-import geometry roundtrip checks passed all 178 FBXs. The corrected native `.blend` is intentionally not included because Blender’s custom-normal re-encoding altered some pre-existing degenerate bevel normals. The original native file remains available, and corrected future cube/UBX generator source is included. This does not change the requirement for the Unreal sample visual test.
