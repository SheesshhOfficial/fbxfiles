# You want it You get it: complete store v1

64 × 56 m, single-floor premium grocery store with all departments, customer/staff toilets, road and forest scenery. This is the complete Blender source successor to the historical pantry slice.

## Download and open

1. Download all five `.part` files plus `Reassemble_Windows.cmd` from [source](source/) into the same folder. GitHub's Download ZIP for the repository also works, but includes all historical packages.
2. Double-click `Reassemble_Windows.cmd`. It uses built-in Windows PowerShell, checks each part and the final SHA-256, and does not overwrite a different existing ZIP. No Python installation or global execution-policy changes are needed. Windows execution has not been tested here; the equivalent Python helper was tested with successful, missing, altered and existing-output cases.
3. Extract the verified `You_Want_It_You_Get_It_Full_Source_v1.zip` and open `premium_store_full_v1/YOU_WANT_IT_YOU_GET_IT_FULL_v1.blend` in Blender 4.3.2 or compatible. All 71 textures are packed; no other package is required to open it.

Python users can download `Reassemble.py` and `ARCHIVE_SHA256.json` alongside all parts, then run `python Reassemble.py`.

The optional [rebuild dependencies](rebuild_dependencies/) are only needed to rerun the source-building scripts. Reassemble their two parts separately and extract beside the full-store folder. Read the included `REPRODUCE.md`.

## Checked source inventory

- Every one of 5,574 eligible placements has its own stable object ID and individual StaticMeshActor/Prop import intent, across 50 types.
- 116 physical canonical assets and 231 convex collision hulls; compound fixtures preserve intentional openings.
- 37 routes, 11 doors and ten starts; full floor, roof and closed interior gameplay boundary checks pass.
- 330 cold products have open-front access; 30 deli/meat/fish products use checked staff-side approaches behind customer glazing.
- 67 fixture-aligned gameplay lights. One exterior-render sun is excluded from default gameplay lighting.
- Five real review/improvement passes are documented in [the ledger](qa/BUILD_REVIEW_LEDGER.json), including repaired shelf facing, source collision/routes, label normals, cold-stock access and lighting.

[Read the independent source QA summary](qa/FINAL_SOURCE_QA_SUMMARY.md). Final master SHA-256: `6ea633d3dab618fab872f6394480786ee17009e8c9921c1e3fa4f2db002a1cf1`.

Final Cycles views and the complete FBX/PBR derivative are being validated separately and are not yet part of this source checkpoint. Existing slice renders remain historical. Do not use earlier slice FBXs as the final store export.

Unreal import, material compilation, actual single-hit Visibility selection, disguised Character collision, multiplayer and ten-player performance are not tested by Blender checks. The existing game Blueprint is unchanged. Every copy is eligible by export contract; that does not by itself prove dense-shelf first-hit selection or Character capsule fit.
