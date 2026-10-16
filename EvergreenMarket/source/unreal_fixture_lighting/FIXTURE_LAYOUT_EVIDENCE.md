# Source-derived fixture layout: 42 points

- 25 suspended ceiling LED diffuser meshes, each paired one-to-one with an existing housing in the source manifest. The source models strip diffusers, not discrete round bulbs. One PointLight is supplied per diffuser.
- Includes all five rear-service/warehouse fixtures at Blender Y=24 m (UE Y=−2400 cm), alongside the other twenty fixtures.
- Actual source fixture coordinates: Blender X={−18,−9,0,9,18} m; Y={−13,−5,3,11,24} m. Unreal conversion is [100X,−100Y,100Z]. The pattern is regular because the modeled fixtures are regular, not because extra lights were gridded across the store.
- Source procedural evidence: `evergreen_source_v2/source/blender/build_supermarket.py`, lines 216–223. Each modeled diffuser is centered at Z=4.355 m with thickness .025 m; export uses its bottom-center pivot, Z=434.250021 cm. Original retail area lights were placed at Z=4.3 m. New point centers use this same Z=430 cm, below the diffuser by 4.25 cm to avoid embedding the emitter in opaque geometry.
- Manifest provides exact source instance IDs, mesh IDs, source object names, and a matching housing per point. `derive_fixture_layout.py` asserts pairing, identity transforms, and unique positions before writing `fixture_point_layout_v1.json`.

## Conservative starting settings, pending target-engine validation

3000 lumens per point, white, inverse-squared falloff enabled, attenuation radius 900 cm, source radius 2 cm, no source length, movable, shadows enabled. These are deliberately modest starting values in response to an over-bright preview, not measured fixture photometry. Blender's old 850-watt area-light energy is not converted into lumens. Current Unreal source already uses explicit lumens; this is not a diagnosis of a unit-setting bug.

The radius is bounded to limit overlap while reaching the floor from 4.3 m and covering the large actual fixture spacing. Shadow casting is retained to avoid indiscriminate light transmission through shelves and walls. Forty-two movable shadow-casting point lights can be expensive; target-engine profiling and exposure/material checks are required before making quality/performance claims. Do not hide a performance problem by turning every shadow off or adding blanket fill lights. A black ceiling is not evidence by itself that the light count is wrong: geometry, ceiling material, exposure and available indirect lighting also require inspection.

## Exterior fixture coverage included

The expanded patch includes all 15 canopy linear lights and both exterior wall lamps, for 42 point lights total. Source evidence is `build_supermarket.py` line 200 (canopy) and line 509 (wall fixtures).

- Canopy: source X=−700 through 700 cm in 100 cm steps; UE Y=1960.000038 cm. Mesh bottom Z=402.50001 cm, center Z=404.00001 cm. Point Z=398.00001 cm, 4.5 cm below the bottom. Start with 250 lumens and a 500 cm attenuation radius per fixture. The radius reaches the ground from ~4 m while remaining bounded. Dense 1 m spacing still creates overlap, so these emitters use much lower intensity than the ceiling fixtures.
- Exterior wall lamps: mesh center UE [2229.999924, −1100 or −2700, 320.000014] cm, width 20 cm. Points use X=2244.999924 cm, five centimeters beyond the outward +X face, keeping the source radius clear of the opaque fixture. Start with 1000 lumens and a 600 cm radius.
- All 42 points use shadows; canopy overlap makes profiling particularly important. These are initial values, not a target-engine performance or brightness guarantee.
- The 15 refrigerated-case vertical LED strips remain emissive and do not get additional point-light actors in this patch. The JSON explicitly records this exclusion. No directional, sky or rectangular lights are specified. Native source package and mesh data remain unchanged.

## Verification limits

Derived from source manifest and procedural source; no Unreal runtime or viewport validation was available. Both source identities and the manifest SHA-256 are saved in the JSON for reproducibility. Numerical tuning should be checked in the user's target Unreal project, including exposure, occlusion, render cost and warehouse visibility.

## Geometric influence-overlap estimate

`estimate_fixture_overlap.py` samples attenuation-sphere membership on a 10 cm XY grid over X=−2300..2400 cm and Y=−3100..2300 cm, ignoring occlusion and intensity falloff. `fixture_overlap_estimate.json` stores reproducible results. This is not measured lux, shadow rendering cost, GPU time or FPS.

- Floor Z=0: sampled maximum 8 total influencing points; ceiling-only maximum 4, canopy-only maximum 7, wall-only maximum 1. Role maxima occur at different locations and must not be summed.
- At canopy height ~398 cm: sampled maximum 12 total; ceiling-only 4, canopy-only 10, wall-only 1. Exact mathematical boundary points on the canopy centerline could include 11 canopy spheres, including two zero-strength radius-boundary contributions; the grid result is a sampled estimate, not a strict maximum proof.
- At ceiling height 430 cm: sampled maximum 12 total; ceiling-only 5, canopy-only 10, wall-only 1.
- Canopy radius 500 cm gives approximately 302.65 cm horizontal reach on the floor from its ~398 cm mounting height. Dense 100 cm spacing necessarily overlaps; 250 lumens each and a bounded radius reduce over-brightness risk but do not eliminate shadow/render cost. Confirm lighting and profile performance in Unreal before approving these values.
