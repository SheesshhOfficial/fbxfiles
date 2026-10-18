# Premium market: resume safely on Unreal 5.7.4

This folder is **reconstructed support from the published v3 source**, not a recovery of the earlier attachment ZIPs. The existing supermarket and carnival must remain intact. Do not rerun the original UE5.8 importer over the current project.

## First step: inspect only

Pull the repository, open your existing premium supermarket map, stop Play, and paste this in Unreal's **Python** console:

```python
import sys, json, importlib; sys.dont_write_bytecode=True; root=r"G:\Unity Projects\Generated\fbxfiles"; sys.path.insert(0,root+r"\EvergreenMarket\premium_store\ue574_resume"); import premium_preflight574 as pp; pp=importlib.reload(pp); print(json.dumps(pp.inspect(),indent=2))
```

The helper does not open/switch maps, import assets, save files, edit actors, change collision, or touch Blueprints. If the carnival or another map is open, it tells you to open the premium map yourself. Save your own work before switching maps. Dirty work is reported rather than saved or discarded.

The last confirmed premium map was:
`/Game/PremiumStoreV3/FullPreview574_v001/Maps/L_V3_AllPlacements`

A later UV-repair map may exist; the report must establish what is actually open. Do not assume the two-mesh UV repair succeeded: its last reported attempt stopped at a dirty-content guard before mutation.

Send the printed report. This is **not** a full-import command or permission for a map-changing second step.

## Next stage, after the report is reviewed

Prepare a new uniquely named premium test-map copy, reusing existing imported meshes/materials. The current map and shared assets will not be overwritten. This stage is not included or launched by the read-only helper.

The first environment-only test will contain a deliberately accessible product and a floor-level hiding area. The existing Character capsule is 70 cm wide and 180 cm tall; it cannot enter the approximately 35 cm gaps between shelf boards. No Blueprint edits are part of this workflow.

The original shelf collision was inspected and follows boards, posts, backs and bases. Removing all shelf collision would create unsafe clipping rather than fix the unchanged character shape. The new approach keeps structural blocking and creates usable space around it.

The existing selection logic historically used one complex Visibility sphere, radius100 cm, centered at ActorLocation+(0,0,10). Its current runtime behavior still needs testing. A Prop actor tag alone does not ensure that the single-hit query reaches the desired object.

## Verification limits

The helper reports loaded editor actors and currently readable mesh definitions. It cannot prove unseen/unloaded world-partition content, cooked collision correctness, exact FBX provenance, source geometry fidelity, material visual parity, Blueprint selection behavior, or multiplayer performance from counts alone. Missing optional APIs/data are reported explicitly.

Offline fake-object tests are separate from running this in your Unreal Editor. No native Unreal test has been claimed for this reconstructed helper before your report.

## Source

Repository: `SheesshhOfficial/fbxfiles`.
Published v3 baseline: `fbf65a7bfcfda6c0ea3484d7b1879756defbd2fb`.
Repo inspected at: `ae938af1ff729fb83874f2844bc0d7dbc91fce3d`.
All premium paths were unchanged between these commits. The original packed Blender source and FBX/PBR archives stay in their existing folders; this helper does not duplicate or replace them.
