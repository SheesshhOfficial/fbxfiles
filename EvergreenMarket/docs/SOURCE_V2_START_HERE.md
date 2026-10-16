# Evergreen Market Source v2: complete source and fresh export

Keep your working Unreal map. This version uses new output folders and unique Unreal map/asset paths. It does not require deleting Content/EvergreenHandoff or changing BP_propChar.

## What is included

- Corrected native Blender source, all 256 canonical render meshes and the original 11,316 placements.
- Corrected FBX geometry with original material/UV associations. Only verified inward-facing closed shells were reversed; open geometry was not blanket-flipped.
- Source-visible collision collections, exported collision companion meshes, an explicit per-placement walking policy, and existing prop query hulls.
- Source-visible neutral preview-light positions and typed Unreal settings. The original Blender lights remain in the source. Blender wattage and Unreal lux/lumens are not treated as equivalent.
- Fresh-import scripts, export validation and local tests. No Unreal runtime is available in the build environment; in-editor sample and walking tests remain required.

## Download and extract

Download every part in this folder and Reassemble_Source_v2_Windows.cmd into one folder. Double-click the .cmd file. It uses built-in Windows PowerShell, verifies every part and the complete ZIP, and will not replace a different existing ZIP. No Python installation or execution-policy change is required.

Extract Evergreen_Market_Source_v2_Complete.zip into C:\Art. The resulting package folder should be C:\Art\Evergreen_Market_Source_v2. Do not mix its files into the older handoff or normals patch.

## Collision behavior

There are separate source-defined bodies for asset queries and environment walking. This keeps doorways and shelf openings available while physical fixtures block movement. Decorative labels, trim and foliage do not each need a solid walking volume. The collision policy records each role and the deliberately nonblocking exceptions.

All 51 disguise-candidate FBXs contain named UBX simple collision inside the FBX itself (111 render FBXs total). Those asset hulls respond according to the Unreal component collision profile; they are not inherently query-only. Physical fixtures also have separate exported UBX-bearing companion FBXs. A render-only fixture dragged into a map alone may have no walking collision: use this package's importer, which applies the matching source-defined walking boxes and per-placement masks. The four tested pilot props are tomato can, coffee can, oats carton and shipping box. Only these four are converted into individually tagged StaticMeshActors by the compatibility stage; the remaining repeated stock stays instanced.

The full physical-fixture audit adds missing blockers, including the impulse displays, chilled cases, entrance planters, lockers and bakery cabinets. Read qa/physical_additions_report.json for the final validated count and exact source evidence. Existing reviewed environment blockers are retained.

## Source edits and exports

Open Evergreen_Market_Source_v2.blend and inspect the named collision and light collections. The guarded exporter checks the native geometry, UV/material associations, placement transforms, exact export-normal attributes and collision definitions before exporting. It refuses geometry changes that would make its approved canonical payloads stale. This is a reproducible approved source snapshot, not an unrestricted exporter for arbitrary edits; changed geometry requires a new validated baseline.

Use the included fresh-import entrypoint and its documented dry-run first. Do not run the old original-package-plus-normals-patch starter on this package. Save all existing editor work before executing any map-changing stage.

## Acceptance in Unreal

1. Check the sample in Lit mode, especially checkout faces, shopping bags, carton and impulse display. Check Static Mesh Editor simple collision display.
2. Run the full import only after the sample passes and looks correct.
3. Walk into the impulse display, chilled case, planter, locker, shelves and known wall. Verify entrance/service passages remain usable.
4. Test E on the four pilot props, then walk against the same known blocking wall and fixtures. Keep your existing prop-hunt GameMode.
5. Test server/client behavior before treating the map as multiplayer-ready. Lighting is a neutral starting layout, not a finished production pass.

## If only the transformed player clips

The supplied Blueprint screenshots show SetStaticMesh followed by fixed relative Z offsets (96 or -0.8). They do not show a capsule-sizing operation in the visible portion. Inspect the continuation before changing gameplay code.

Blender simple collision does not automatically resize a Character's movement capsule or change its child PropMesh offset. If normal characters block correctly at the same fixture while a disguise extends through it, compare the runtime capsule size, component hierarchy/scale and PropMesh relative location with your already-working imported props. Do not enable moving complex collision or simulate physics blindly.

Epic's movement documentation explains that swept movement checks its UpdatedComponent; attached components move to the destination without separate sweeps:
https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UMovementComponent

FBX collision conventions:
https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine

## Exact commands

Follow [source/unreal/FRESH_SOURCE_V2.md](FRESH_SOURCE_V2.md) for the checked Windows paths, bootstrap and explicit stages. The bootstrap performs preflight only. The sample receives its own neutral lighting before the full-import visual approval gate.

For source export instructions and known Blender display-normal limitations, see the Blender source documentation supplied in this package. The exact corner-normal attribute, not Blender's lossy viewport reconstruction, is the validated export authority.
