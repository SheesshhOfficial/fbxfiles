# Target-project acceptance checklist

No Unreal execution occurred in this build environment. Complete this in the user's actual game project before treating the candidate as playable. Prepared Editor Python helpers are supplied for review; a `.uproject` or saved `.umap` is not included.

## Import and dimensions
- Back up the game project, save current map changes, and inspect `unreal/ENVIRONMENT_IMPORT.md`.
- Import the matched current manifests, FBXs and textures together. Do not mix the archived checkpoint.
- Validate a known 1 metre dimension becomes 100 Unreal units. Confirm orientation, zero actor rotations and unit scales before placing all assets.
- Confirm ten actual PlayerStart actors and 153 separate eligible StaticMeshActor placements. Shared mesh assets are expected; HISM or merged eligible copies are not.
- The helper refuses existing target assets/maps to avoid overwriting unrelated project work. Inspect any partial import before retrying.

## Collision and movement
- Inspect imported UCX in the Static Mesh Editor and in the level with collision visualization.
- Check all perimeter sections, floor seams, entrance gate, stall counters, carousel steps, bumper-arena entry, cockpit interiors, funhouse mouth/rear exit and trailer steps.
- Move the actual game capsule through each route and each intended hiding location. Pay special attention to pallets in the maintenance passage and mirrors in the funhouse.
- Collision uses compound solid parts for gameplay-useful openings, with simpler whole-volume proxies allowed on small objects whose tiny openings cannot fit players. Thin foliage/decorations and some concave details are intentionally omitted. Do not auto-convex a whole zone or tile to fill gaps; this would seal openings.
- Test floor/bounds and fall recovery, sightlines, spawn clearance, crowding with ten players and no unreachable eligible stock behind sealed glass.

## Existing possession Blueprint
Preserve the user's existing BP_propChar behavior while integrating: E uses a reliable Server path, a Visibility sphere trace of radius 100 at ActorLocation + Z10, then casts the hit actor to StaticMeshActor and checks PropActor tag OR the project whitelist. Tagging copies does not by itself validate server authority, replication or collision responses.

- Confirm each eligible copy independently yields its own StaticMeshActor when hit.
- A single-hit Visibility sphere trace returns only its selected blocking hit. Floors, rails or other scenery can be returned first, and a tag test then rejects that hit without searching farther. Reproduce this using the actual trace visualization and collision-response settings before deciding whether the project needs a reviewed trace-policy change. The supplied map importer does not change this Blueprint.
- Test large and small props, low camera positions, nearby floors/walls, duplicated assets and both tag/whitelist branches.
- Test possession, release, client/server ownership, collision size, camera offsets and replication with multiple clients. Source Blender checks cannot establish these behaviors.

## Materials, atmosphere and performance
- Verify UV density, material-slot assignment and imported split normals on the trailer roofs, bevels, bumper cars and foliage. Raw environment FBX normals match source, but Blender reimport re-encodes some bevel-corner normals differently; inspect the listed affected assets in the actual Unreal importer.
- Review NormalGL green-channel conversion, roughness, metallic response and two-sided leaves. Blender procedural modulation is not automatically identical to the prepared Unreal material approximation.
- Glass uses a documented translucent approximation; tune opacity, IOR/refraction, sorting and shadows in the target renderer. Mirror surfaces need an actual target-engine reflection solution.
- Source lights are metadata-based approximations; tune exposure, brightness, color, attenuation, shadows and cost. The Blender moon and haze are render-only and excluded from static meshes.
- Review all 24 environment tiles and both pallet assets listed in export/qa/*reimport_caveat.json under target-engine lighting before accepting normals/tangents.
- Profile the dense source foliage and approximately 3.54M visible source triangles on target hardware. Add suitable LODs/culling/instancing for non-eligible decoration; preserve independent eligible actors.
- Audio, animated rides, runtime effects and multiplayer game rules are not implemented by this asset bundle.

## Sign-off evidence
Record engine version, import settings, map name, actual player capsule dimensions, client count, representative trace tests, collision screenshots, frame-time/profile captures and remaining defects. Source QA and Blender FBX roundtrip evidence are useful inputs, not substitutes for these engine tests.

## Python module cache
Start a fresh Unreal Editor session before switching from an older carnival importer to V2. The helper module names are shared; Python can otherwise reuse an already-imported older helper from its module cache. Verify the loaded helper file paths point to this package before executing.
