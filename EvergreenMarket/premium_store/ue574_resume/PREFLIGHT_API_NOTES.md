# Read-only preflight: API evidence and limits

The public entry point is premium_preflight574.inspect(). Importing the module performs no Unreal operation. It returns a JSON-serializable dictionary and performs no file writes.

This module was tested with offline fakes, not inside a live Unreal Editor. Epic publishes the Python reference for the 5.7 branch, not a separate 5.7.4 patch reference. Therefore the module reports actual engine version, missing APIs and unreadable properties, and does not claim that documentation or offline tests establish native execution.

## Read APIs checked against official Epic 5.7 documentation

- [UnrealEditorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/UnrealEditorSubsystem?application_version=5.7): gets the current editor world without opening a map.
- [EditorActorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorActorSubsystem?application_version=5.7): enumeration covers loaded editor actors and excludes PIE/preview actors. Unloaded World Partition actors are outside this snapshot.
- [_ObjectBase API index](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/genindex-G?application_version=5.7): inherited get_world, get_class, get_path_name and property reads support object identity checks.
- [Actor](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Actor?application_version=5.7): component reads, actual location and network role. Label reads explicitly pass False to prevent the default label-creation behavior.
- [EditorLoadingAndSavingUtils](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorLoadingAndSavingUtils?application_version=5.7): dirty map/content package getters only. The module does not use this class's load/save/import methods.
- [AssetRegistry](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetRegistry?application_version=5.7) and [AssetData](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetData?application_version=5.7): cached on-disk metadata through recursive get_assets_by_path. No registry rescan, get_asset, or asset load. is_loading_assets only reports the initial scan; a false value is not proof of a fully current registry.
- [PrimitiveComponent](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PrimitiveComponent?application_version=5.7): collision enabled/profile/object type and Pawn/Visibility response getters.
- [BodySetup](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/BodySetup?application_version=5.7) and [KAggregateGeom](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/KAggregateGeom?application_version=5.7): collision trace mode and aggregate shape arrays on already-referenced meshes.
- [StaticMeshEditorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMeshEditorSubsystem?application_version=5.7): convex/simple collision counts and UV-channel count reads. Negative results are reported as unavailable, never as success.
- [EditorLevelLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorLevelLibrary?application_version=5.7): get_pie_worlds(True) detects already-running PIE worlds. This API can be unavailable if its editor plugin is not enabled; the report then says PIE state is unavailable.
- [GameplayStatics](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/GameplayStatics?application_version=5.7), [Character](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Character?application_version=5.7) and [CapsuleComponent](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/CapsuleComponent?application_version=5.7): only after premium PIE is observed, read player index 0, current capsule, roles and actual loaded StaticMesh components. This does not enumerate every remote player or validate replication.

## Interpretation

- Source references are 6,593 placements, 5,574 Prop placements, 264 canonical meshes, 235 canonical UCX hulls, 67 fixture lights, ten spawn markers, four boundary metadata markers and four boundary barriers.
- Ownership uses PremiumStoreV3, V3Placement=..., V3Asset=... and V3Phase=full. Missing, duplicated or empty identity tags are diagnostic exceptions. Placement classes must be native StaticMeshActor.
- Shelf reference: SM_EG_PremiumShelfBay, 12 convex hulls. Refrigerated bay: SM_FULL_OpenFrontRefrigeratedBay, ten. The can representative includes crushed_tomatoes / SM_MV_crushed_tomatoes.
- Convex counts do not establish UCX origin, geometric equivalence or successful cooked collision. Imported collision settings are observational, not movement/trace approval.
- The historical single complex Visibility sphere of radius 100 cm, with start and end at actor location plus 10 cm vertically, is labeled historical and unverified against the current Blueprint. No trace is executed and no Blueprint graph is opened, changed or compiled.
- A non-premium editor map returns OPEN_PREMIUM_MAP_FIRST and skips editor actor/component and PIE pawn reads. It never changes the map or saves/discards existing work.
- Dirty package lists are read before and after. Equal lists do not prove no other editor activity occurred; changed or unreadable lists require review.
- Output lists are capped. All returned editor actors are inspected; representative groups show up to three examples each.

## Offline checks

Run python -m unittest discover -s tests -v from the delivery folder. The builder's standalone suite contains 22 tests with forbidden mutation/load/trace traps. It covers wrong-map isolation, exact engine versions, dirty work preservation, optional API failures, ownership/class regressions, duplicate canonical mappings, known representatives and PIE actual-mesh reporting. The separate independent suite adds 13 tests.

No live project, Blueprint, material, collision asset or map was modified during these tests.
