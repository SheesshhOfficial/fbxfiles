SNIPERSAIM — DENSE CANYON V2
Editable actual-asset environment, rebuilt 16 October 2026.

OPEN
Open SnipersAim_Dense_Canyon_v2.blend in Blender 4.3.2 or compatible later version. All 59 working texture images are packed into the file; no external texture folder is needed to view the Blender scene. The file opens on the overview camera. Four named cameras provide overview, topdown, sniper and runner views. Source masters are hidden in SOURCE_MASTERS and can be reused; visible copies share their mesh data.

WHAT CHANGED
The earlier plan had isolated obstacles roughly 15–20 m apart along the advance. This rebuild has 56 primary cover stations, one open arch landmark reserved within the left route, 24 cargo pieces and two final-approach covers: 83 cover objects total. Three interleaved lanes have nominal 8.35 m forward station spacing, with varied sideways offsets, rotations and asset combinations. The arch replaces one regular station to keep its aperture open.

Consecutive lane-station planar bounding-box edge separations: minimum0 m, median2.03 m, maximum5.07 m. Zero means projected boxes overlap, not that actual meshes touch or form an impassable wall. These numbers are approximate footprint proxies, not collision-tested walking distances. The older scene was unavailable locally, so the before comparison uses its prior documented plan, not a fresh measurement of that file.

STATIC GEOMETRY CHECKS
53 of 56 primary cover stations have a sampled standing-body hiding location where five rays (feet, torso, head at1.8 m, and shoulders) toward the sniper eye hit that station's actual mesh. Three stations remain partial/peek cover: centre lane S15 L-barricade, centre lane S19 Baricade3, right lane S19 boulder. These have nearby alternate cover. The test samples candidate positions outside each object's projected bounding box; it does not validate capsule occupancy or movement.
14 of54 sampled transition midpoints have a torso sightline to the sniper when tested against cover meshes. Other transitions can have exposed portions not represented by that midpoint. This is evidence of both hiding and shooting opportunities, not a balance guarantee. Gate-centre rays at x=-0.75,0,+0.75 m and heights0.2,1.0,1.8 m were clear through the exit approach. The tower deck and added forward firing balcony were measured at z≈21.964 m, with sniper eye at23.55 m. The added3.2x4 m steel balcony allows a supported stance ahead of the original top rail, keeping the near approach visible.

SCALE / ANCHORS
1 Blender unit =1 metre. Reference runner height1.8 m.
RUNNER_SPAWN=(0,-87,0)
EXIT_GATE=(0,89,0)
SNIPER_EYE=(0,85.8,23.55)
Tower height26 m. Main straight spawn-to-exit displacement176 m. Ground64x224 m includes presentation margins; usable width varies with rock faces, approximately36–38 m. Cover heights mostly2.6–4.3 m, with lower cargo and taller final pieces.
The requested120-second round is a gameplay target only. There is no timer, movement implementation or measured completion time in this environment.

SOURCE / FILE SIZE
Original assets: https://github.com/SheesshhOfficial/fbxfiles.git
Pinned commit:5ae8afdb0ae6519261049e15dc388da1cf7f99b1
14 FBX models plus one rifle GLB. Embedded original4K materials were inspected. This compact working scene uses1K source-derived textures, with non-destructive source preservation in the downloaded repository. Dense L-barricade and rifle working meshes were simplified to about100,000 faces each. The rifle is display geometry only.
119 visible mesh objects share19 unique mesh datablocks: the15 supplied models, ground, and three simple authored firing-balcony pieces. Repeated asset placement therefore does not duplicate Blender mesh/texture data for every copy. This does not eliminate draw calls, visible triangle processing or Unity performance concerns. No claim is made that a full-scene FBX preserves equivalent sharing without checking it.

UNITY REUSE
Prefer importing each distinct working asset once, creating a prefab with shared mesh/material/texture references, then placing prefab instances. Use Layout_Manifest.json for source IDs and transforms. This avoids importing the same large source FBX repeatedly under different filenames. GPU instancing, batching, LOD and platform compression still need separate profiling.
The working source meshes are normalized to height1 m, bottom at z0 and horizontal centre at origin. Manifest scales apply to those normalized meshes, not directly to raw original FBXs. Geometry normalization is reproduced by inspect_build.py.
Blender coordinates (X,Y,Z) map to Unity (X,Z,Y), and Blender positive Z yaw maps to negative Unity Y yaw for equivalently converted mesh coordinates. The manifest provides unity_position_xyz, unity_yaw_degrees and unity_scale_xyz. If a model importer already transforms axes through an extra parent, avoid applying the conversion twice. Check a labelled anchor and one rotated asymmetric barricade before batch instantiation.

NOT YET TESTED
Unity importing/render pipeline, colliders, capsule clearance, navmesh, LODs, performance, actual shooting/movement,120-second balance and multiplayer. No playable Unity project is included. The collapsed arch has rubble at its threshold; physics/collision must preserve its visual opening appropriately. Lighting and procedural ground material require engine-specific recreation.

KEEPING / REBUILDING
Download the blend and reconstruction ZIP to storage you control. Temporary cloud workspace persistence is not guaranteed. The reconstruction package contains the complete authored Python build scripts, pinned source reference/checksums, layout manifest and QA reports. It can reconstruct the scene from the original repository if the binary working file is lost. GitHub source availability and the recorded commit must remain accessible.
