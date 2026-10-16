# Original-placement prop batch audit

Status: offline selection reviewed; not executed in Unreal.

16 original instances: 14 low endcap cans, bottles and cartons, plus 2 pallet-level stockroom boxes. All source transforms are retained verbatim, including sub-micro unit-scale residuals. No new duplicate props or relocations are proposed.

The original scene has 11,316 logical placements, including 6,695 disguise candidates. This batch covers only 16 candidates and explicitly excludes the four staged pilot source IDs. The existing 694 walking-collision boxes are used for geometry diagnostics and must remain unchanged.

## Selected placements

| Instance | Mesh name | Original XYZ cm | World bottom/top cm |
|---|---|---|---|
|EGI_0f8d6343f4f54f9d|SKU_02_bottle|-762.00, 849.00, 45.00|45.00, 79.70|
|EGI_5451cd109bab56e9|SKU_02_bottle|-840.00, 351.00, 45.00|45.00, 79.70|
|EGI_01eca130f35d655e|SKU_03_bottle|-162.00, 351.00, 45.00|45.00, 79.70|
|EGI_7ff75102d10dd13b|SKU_03_bottle|-240.00, 849.00, 45.00|45.00, 79.70|
|EGI_4c0fd92658e86b28|SKU_04_bottle|438.00, 849.00, 45.00|45.00, 79.70|
|EGI_3ba9a0d6328c5647|SKU_05_Carton|960.00, 351.00, 45.00|45.00, 74.00|
|EGI_3013a88f914ebc03|SKU_06_can|-762.00, -399.00, 45.00|45.00, 63.50|
|EGI_869f7db65feb4ccd|SKU_06_can|-762.00, 99.00, 45.00|45.00, 63.50|
|EGI_33de12349a45541a|SKU_07_can|-240.00, -399.00, 45.00|45.00, 63.50|
|EGI_9dfa86a010edad0a|SKU_08_can|438.00, -399.00, 45.00|45.00, 63.50|
|EGI_b74ac46863b43864|SKU_10_Carton|-762.00, -651.00, 45.00|45.00, 74.00|
|EGI_4c207ecbd1ac569b|SKU_11_bottle|-240.00, -1149.00, 45.00|45.00, 79.70|
|EGI_4fb051d8175da0d7|SKU_12_Carton|438.00, -651.00, 45.00|45.00, 74.00|
|EGI_18fc8f491c214f5f|SKU_13_can|960.00, -1149.00, 45.00|45.00, 63.50|
|EGI_40290a2b7eaefcbc|ShippingCarton_Floor|271.00, -2767.24, 23.00|23.00, 71.70|
|EGI_9ca5fc6b0e622d49|ShippingCarton_Floor|-1571.00, -2467.24, 23.00|23.00, 71.70|

## Accessibility review

The fourteen sales-floor candidates are on the lowest endcap shelf at approximately 45 cm above world origin, facing cross-aisles at the ends of the gondolas. Their highest point is below 80 cm. The two shipping cartons are at 23 cm and reach 71.7 cm; these are pallet-level stockroom placements, not free objects directly on a floor.

The endcaps span the original x=-800,-200,400,1000 cm gondola groups and y≈849,351,99,-399,-651,-1149 cm cross-aisle sides. The two boxes extend coverage to the rear stockroom. These positions are more plausible first candidates than high shelves, but walking routes and selection still require the real character in PIE.

For each candidate the JSON records the original transform, transformed canonical world AABB, an illustrative probe center 80 cm toward the facing cross-aisle, and all authored walking boxes within a hypothetical 100 cm sphere of that point. This is a conservative AABB proximity review only; no actual trace has been simulated. The floor, shelves, neighboring props, backing or pallet can win the first Visibility hit. The supplied Blueprint screenshots show a 100 cm-radius Visibility sphere with identical start/end at ActorLocation + (0, 0, 10), ignoring self. The character actor/capsule center height and actual first hit still need a PIE check; the illustrative probe is not a simulation of that Blueprint.

Do not change fixture collision to force a passing interaction. Test each candidate from its adjacent aisle with the actual character, inspect the returned hit actor/component, and verify movement remains blocked by the preserved fixtures. If a candidate fails, leave it unconverted or choose a separately reviewed original instance; do not silently move or duplicate it.

## Provenance and tests

Source: evergreen_source_v2/manifest.json, setup_prop_actor_pilot.py selection logic, setup_market_collision.py and collision_policy_v2.json. Canonical bounds are bottom-center full dimensions transformed using source quaternions and scales.

Reproduce with python prop_batch_work/generate_prop_batch_selection.py and python prop_batch_work/test_prop_batch_selection.py. Eight tests cover explicit uniqueness/count, exact transform equality, pilot exclusion, canonical scale/category, low heights, spatial distribution, 694-box/source counts, manifest fingerprint and deterministic reproduction.

Manifest SHA-256: e983146c1d8f18145eaec63c9ec0544e3a6128231b7c61eb940bcace94566f85
