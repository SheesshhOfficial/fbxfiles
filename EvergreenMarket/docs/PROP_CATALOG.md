# Evergreen Market: logical prop catalog

This catalog defines complete visible objects for the Unreal handoff. A mug
includes its handle, a carton includes its tape and label, and a cart includes
its basket, frame, handle and wheels. Repeated copies can share a logical mesh
while retaining separate scene placements.

The eligibility tiers below are starting recommendations for prop-hunt testing.
They do not establish working disguise behavior, collision, navigation, network
replication, performance targets or playtested balance.

## Default disguise candidates

| Complete prop | Scene copies | Included details |
|---|---:|---|
| Shipping carton | 466 | Box, packing tape, printed label and handling text; three size variants |
| Empty produce crate | 30 | Base, all side/end slats and four corners |
| Shopping basket | 7 | Base, slotted sides, ends and continuous rim |
| Staff chair | 4 | Seat, back and four steel legs; opposite-facing placements use the same chair design |
| Utility bin | 3 | Bin body and lid |
| Paper shopping bag | 12 | Bag and handle |
| Coffee machine | 1 | Body and front plate |
| Microwave | 1 | Body and door glass |
| Wet-floor sign | 1 | Tilted sign body and warning lettering |
| Fire extinguisher | 3 | Cylinder, bracket and hose |
| Potted herb | 3 | Pot and complete foliage; three foliage variants preserve the authored appearance |

These 531 placements are proposed candidates, not a final gameplay allowlist.
Thin profiles, handle gaps, material transparency and wall-mounted starting
positions still need review in the intended game mode.

## Conditional: small or flat objects

| Complete prop | Scene copies | Important condition |
|---|---:|---|
| Packaged grocery products | 5,270 | Preserve 17 SKU/shape combinations and their label materials; require minimum-size and visibility rules |
| Fruit | 600 | Five fruit types; each has 90 plain and 30 stemmed copies |
| Crusty loaf | 162 | Loaf includes all three scoring details |
| Bakery roll | 36 | Already a complete one-piece mesh |
| Ceramic mug | 4 | Body and handle form one prop |
| Baking tray | 6 | Very low silhouette; requires explicit flat-prop rules |

Small objects can be difficult to see or hit at normal player distance. Test
minimum world size, camera behavior and collision independently of their visual
mesh. Stems, labels, scoring marks and handles are details, not extra disguises.

### Grocery SKU guide

The 16 original package labels map to these complete product families. The
yogurt label has both a can and a carton shape, making 17 shared product
archetypes in total.

| SKU | Brand and product | Package tagline | Complete mesh family |
|---|---|---|---|
| 00 | FIELD Oats | Wholegrain | `SKU_00_Carton` |
| 01 | SUNRISE Corn Flakes | Golden & Crispy | `SKU_01_Carton` |
| 02 | ORCHARD Apple Juice | Pressed Daily | `SKU_02_bottle` |
| 03 | GROVE Orange Juice | Sun-Ripened | `SKU_03_bottle` |
| 04 | RIVER Sparkling | Mineral Water | `SKU_04_bottle` |
| 05 | CLOUD Oat Drink | Original Blend | `SKU_05_Carton` |
| 06 | PANTRY Tomatoes | Vine Ripened | `SKU_06_can` |
| 07 | HARVEST Garden Peas | Sweet & Tender | `SKU_07_can` |
| 08 | EMBER Coffee | Dark Roast | `SKU_08_can` |
| 09 | MEADOW Herbal Tea | Mint & Lemon | `SKU_09_Carton` |
| 10 | GOLDEN Pasta | Durum Wheat | `SKU_10_Carton` |
| 11 | PURE Clean | Surface Spray | `SKU_11_bottle` |
| 12 | DAIRY Fresh Milk | Whole Milk | `SKU_12_Carton` |
| 13 | DAIRY Yogurt | Natural | `SKU_13_can` and `SKU_13_Carton` |
| 14 | CRISP Potato Chips | Sea Salt | `SKU_14_Carton` |
| 15 | BLOOM Soap | Citrus & Sage | `SKU_15_Carton` |

For the tomato-can example, SKU 06 PANTRY Tomatoes is one complete shared can
archetype, including the can body, ends/rims and tomato-label material. Its
303 source placements reference that shared design while retaining their
individual positions, rotations and scales. It belongs to
`conditional_small`, so enable it after the small-prop gameplay checks.

## Conditional: large or low-profile objects

| Complete prop | Scene copies | Included details |
|---|---:|---|
| Shopping cart | 7 | Wire basket, frame, handle and four complete casters |
| Wood pallet | 75 | Three stringers and five deck boards |
| Cleaning trolley | 1 | Base, four casters, two buckets with dark openings and both cleaning handles |
| Pallet jack | 1 | Hydraulic body, forks, wheels and handle |
| Commercial refuse container | 2 | Body, lid, four casters and recycling label |

These 86 placements need route-clearance and silhouette review. Pallets need a
specific low-profile rule. Do not also spawn the cleaning trolley's included
buckets or wheels as independent copies of the same visible geometry.

## Exported family names and eligibility

Mesh asset IDs use `SM_EG_<family>_<geometry hash>`. The generated asset manifest
provides each exact filename, bounds, instance count, category and tier; use
those fields rather than interpreting the hash.

| Tier | Exported family names |
|---|---|
| `default` | `ShippingCarton_Rack`, `ShippingCarton_Floor`, `ShippingCarton_Yard`, `ProduceCrate`, `ShoppingBasket`, `StaffChair`, `UtilityBin`, `PaperShoppingBag`, `CoffeeMachine`, `Microwave`, `WetFloorSign`, `FireExtinguisher`, `HerbPlanter_V01` through `V03` |
| `conditional_small` | `SKU_00` through `SKU_15` families with their authored `Carton`, `bottle` or `can` shape suffixes |
| `conditional_tiny` | `CeramicMug`, `CrustyLoaf`, `BakeryRoll`, and `Fruit_<type>_Plain` / `Fruit_<type>_Stemmed` |
| `conditional_tiny_flat` | `BakingTray` |
| `conditional_large` | `ShoppingCart`, `CleaningTrolley`, `PalletJack`, `CommercialRefuseContainer` |
| `conditional_large_flat` | `WoodPallet` |
| `fixed_scenery` | `SafetyBollard`, numbered `StaffLocker` variants, `StaffTable`, `StaffKitchenette`, `BakeryWallCabinet`, `BakeryIsland`, `ProduceIsland` |
| `fixed` | Remaining individual scenery/fixture asset families |

All candidate tiers carry category `disguise_candidate`; fixed tiers carry
category `scenery`. Enable only `default` initially. Conditional tiers need an
explicit gameplay decision, and fixed tiers should remain ineligible.

## Fixed scenery by default

Keep structural surfaces, doors/glazing, roof equipment, ventilation, fences,
lighting, service signs, attached posters and permanently mounted fixtures out
of the default disguise pool.

The catalog also identifies these complete fixed assemblies:

- Four safety bollards, each including its reflective band
- Six numbered staff lockers, each including door, vents, handle and number
- One staff table including four legs
- One kitchenette including worktop, sink and tap; appliances remain separate
- Three bakery wall cabinets including shelves, uprights and top light
- One bakery island including countertop and sneeze glass
- Five produce islands including their worktops and legs; crates, fruit and
  signage remain separate

Grocery gondolas, warehouse racks, refrigerated cases, freezer islands,
checkouts, promotional islands, entrance planters and rooftop air-handling
units are also fixed scenery unless deliberately added to a separately tested
large-prop mode. Their stocked products remain independent logical objects.

## Assembly and review rules

1. Preserve the full visible prop. Do not export a handle, label, wheel or slat
   as the selectable representation of its complete parent object.
2. Keep loose products separate from shelves, crates, trays and counters.
3. Preserve materially or visibly different variants. Matching geometry alone
   is insufficient when package labels or sign lettering differ.
4. Preserve the scene's authored placements and metre scale. Configure the
   Unreal import scale explicitly and verify familiar real-world dimensions.
5. Validate the assembled bounds, floor pivot, collision and player-facing
   behavior before enabling a family as a disguise.

The complete-object grouping was checked against the native authored scene:
1,446 placements contain 5,117 source components, with no duplicate component
assignments and no grouping errors. This check covers the assemblies cataloged
above; the separate Unreal import and gameplay checks remain necessary.
