# Independent read-only preflight review

Reviewed 2026-10-18. Scope: standalone `preflight/premium_preflight574.py` and `delivery/README.md`, for the existing premium supermarket in Unreal Editor 5.7.4. This is source review and offline testing, not a native Unreal execution result.

## Verdict

**PASS for the bounded read-only diagnostic stage. Native Unreal execution remains NOT_RUN.** The helper is not authorization or a technical gate for any later map-changing task. Preserve the existing premium map and the completed carnival. Do not include the reference importer as this stage's entrypoint.

Reviewed module SHA-256: `361fde7cdfbc01a4d6962216037ed59877b6a4cbab5cd884ef5549612ce7d331`.

## Independently verified

- No production calls that save, load/import assets, load/switch maps, spawn/delete/duplicate actors, edit properties, alter selection, force registry scans, execute traces, access the Library, or use network/file-writing APIs. Imported production dependencies are `collections`, `math`, `re`, and lazy `unreal` only.
- Engine method dispatch has an explicit read-method allowlist. Attempts to call a setter through it are rejected before reaching the fake engine object.
- Actor labels are read with `get_actor_label(False)`, avoiding the documented label-creation default.
- Engine identity matches exact `5.7.4` plus a build suffix, rather than accepting `5.7.40`, `5.7.4.1`, or arbitrary suffix text.
- A nonpremium current map, including the corrected carnival and a similarly prefixed `PremiumStoreV3Evil` namespace, returns `OPEN_PREMIUM_MAP_FIRST` and does not enumerate its actors. The helper never opens the premium map for the user.
- Namespace checks are slash bounded. The original map has a separate exact identity check; premium variants are identified for review. Actor tags, native StaticMeshActor class, placement identifiers, mesh references and source counts are observations only, not immutable provenance evidence.
- Missing APIs remain explicitly unavailable. Negative subsystem collision/UV read results are not accepted as real counts. Empty placement/asset identifiers are malformed.
- Dirty-package state is read before and after. A dirty/unknown/changed result cannot produce a complete snapshot status. Neither set is saved or discarded.
- Loaded-actor scope is stated. Collision counts/settings do not claim authored UCX provenance, equivalent geometry, cooked collision, trace reachability, visual parity, or multiplayer validation. The historical trace contract is labeled unverified and is never executed.
- README disables Python bytecode writing before importing. The helper itself writes no report or other file; its return is printed by the console command.

## Tests

Independent suite: `test_review_preflight574.py`.

Final runs: **13 independent tests passed**, plus **22 builder tests independently rerun and passed** (35 total). Tests use frozen fake objects which record method access and reject writes, a miniature source-count contract, and static AST inspection. They cover happy snapshot, label noncreation, wrong-map/namespace guard, exact version matching, negative simple/convex/UV return values, blank tag identifiers, missing optional APIs, dirty-after changes and failures, list-limit validation, and the read-method allowlist.

The miniature explicitly substitutes expected counts to test status logic; it is not a simulation or validation of the user's 6,593-placement map. Test logs and code are offline evidence only.

Four report defects were reproduced before correction: permissive engine suffix matching, unclassified negative count results, clean-before/dirty-after still yielding a complete status, and empty tag identifiers. All four corrected paths pass the final independent suite.

## Official Epic 5.7 API checks

The documentation is versioned at minor release 5.7 and marked experimental; it does not substitute for execution in the user's installed 5.7.4 build.

- [EditorActorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorActorSubsystem?application_version=5.7): `get_all_level_actors` returns loaded editor actors and excludes PIE/preview actors.
- [UnrealEditorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/UnrealEditorSubsystem?application_version=5.7): current editor world retrieval is read-only.
- [Actor](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Actor?application_version=5.7): label creation defaults on unless explicitly disabled; component/location/class-related observations remain separate from editing.
- [Inherited method index](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/genindex-G?application_version=5.7): `get_world` is documented on `_ObjectBase`, inherited by Actor. It need not appear in the Actor class page's own method list.
- [StaticMesh](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMesh?application_version=5.7) and [KAggregateGeom](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/KAggregateGeom?application_version=5.7): loaded BodySetup/bounds and all nine aggregate shape arrays are exposed.
- [StaticMeshEditorSubsystem](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/StaticMeshEditorSubsystem?application_version=5.7): convex/simple counts and UV-channel read APIs exist; negative collision-count results signify unsuccessful queries.
- [AssetRegistry](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetRegistry?application_version=5.7) and [AssetData](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AssetData?application_version=5.7): cached metadata reads are supported. `is_loading_assets` covers initial registry search only, so the helper appropriately reports a snapshot and does not establish complete registry coverage. No `AssetData.get_asset` call is used because that can load assets.
- [EditorLoadingAndSavingUtils](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorLoadingAndSavingUtils?application_version=5.7): dirty-package queries are supported; its mutating methods are not called.
- [EditorLevelLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorLevelLibrary?application_version=5.7): optional `get_pie_worlds(True)` is documented. Unavailable PIE data is reported rather than assumed absent.
- [SystemLibrary](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/SystemLibrary?application_version=5.7): engine version read API is documented.

## Remaining validation

The user's printed report is needed to establish the actual open map, installed API behavior, loaded placement data and current collision metadata. Actual selection/disguise, movement clearance, cooked collision, rendering, and two-client behavior need separately scoped project tests. Counts alone are insufficient.
