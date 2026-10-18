# Prop eligibility tag patch

This additive helper appends the actor tag `Prop` to the exact 153 importer-owned native prop actors in the saved full map. It preserves existing tags, including `PropActor`, and preserves transforms, light edits, components, materials, meshes and Blueprints. Existing `Prop`, `prop` or other letter-case equivalents are left unchanged.

Open `/Game/AbandonedCarnivalFull57_Corrected/Maps/AbandonedCarnivalFull57` and stop Play/Simulate. Dirty map/light edits are allowed. The helper does not save anything. It checks the pinned full importer and original source files, then validates every prop's identity, ownership tags, native actor class and expected `/Props/` mesh path. Missing, duplicate, extra or changed eligible props block the operation before tag mutation.

## Read-only preview

Paste into Unreal's Python console:

```python
import sys, json, importlib; sys.dont_write_bytecode=True; root=r"G:\Unity Projects\Generated\fbxfiles\AbandonedCarnival"; sys.path.insert(0,root+r"\full_import57"); import carnival_prop_tags57 as pt; pt=importlib.reload(pt); prop_preview=pt.preview(root); print(json.dumps({k:prop_preview.get(k) for k in ("status","eligible","needs_tag","already_tagged","errors")},indent=2))
```

Expected: `PROP_TAGS_PREVIEW_READY`, eligible 153. `needs_tag` is how many currently lack the tag; all existing tag lists are available in `prop_preview["actors"]`. Preview creates no transaction and edits no actors or files.

## Apply explicitly

After loading the helper above:

```python
prop_tag_report=pt.apply(root); print(json.dumps({k:prop_tag_report.get(k) for k in ("status","eligible","changed","mutation_attempted","partial","errors")},indent=2))
```

Success is `PROP_TAGS_APPLIED_UNSAVED`, or `PROP_TAGS_ALREADY_PRESENT` if no changes were needed. Save manually when you choose. Apply repeats the complete actor check before mutation and uses each actor's current tags immediately before its setter.

The operation uses one editor transaction and calls `actor.modify()` before each setter. On failure, inspect `prop_tag_report["actors"]` and `errors`. `PROP_TAGS_FAILED_PARTIAL` means modifications were attempted; the report records readback and observed changes. There is no automatic rollback. Editor Undo may revert the transaction; native undo has not been tested by the offline suite. Do not assume an exception restored the previous state.

This patch only supplies the tag used by the existing eligibility rule. It does not modify or validate Blueprint behavior, collision selection, gameplay or visual results.

## Focused tests

```console
python -B -m unittest discover -s tests -p test_prop_tags57.py -v
```

The tests use real frozen placement metadata with fake Unreal objects. They verify fail-closed identity checks, tag preservation, idempotence, unchanged unrelated actors and partial failure reporting. They do not establish a native Unreal runtime pass.

API references: [ScopedEditorTransaction](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ScopedEditorTransaction?application_version=5.7), [Object modify and property setter](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/_ObjectBase?application_version=5.7).
