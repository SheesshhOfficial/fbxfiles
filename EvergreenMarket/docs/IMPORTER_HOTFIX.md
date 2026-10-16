# Importer hotfix: collision enum names (2026-10-16)

The original multipart archive is unchanged. **After extracting it, replace its `source/import_supermarket_unreal.py` with the updated file from this repository's `source/unreal/import_supermarket_unreal.py`.** No FBX, texture, manifest or material data changed.

The original helper incorrectly used `CollisionResponseType.IGNORE` and `.BLOCK`. Epic's Python API uses `.ECR_IGNORE` and `.ECR_BLOCK`. A reported sample imported meshes/materials but stopped while building its first ISM actor. Consequently, `sample_report` was never assigned; the later NameError was a consequence, not a second import issue.

This fix corrects both names and validates collision enums before any content creation. All existing sample/persistence/fingerprint/visual-review gates remain enabled.

## Retry in Unreal
1. Save or discard unsaved changes yourself; stop Play mode. Keep the failed generated folder for inspection.
2. Replace `C:\Art\Evergreen_Market_Unreal_Handoff\source\import_supermarket_unreal.py` with the updated helper.
3. In Output Log's Python mode, run each line:

```python
import importlib
importlib.reload(em)
sample_report = em.run(package, execute=True, phase="sample")
```

If restarting the editor, first repeat the original `sys.path`, `import import_supermarket_unreal as em`, and `package = ...` setup.

The retry creates a fresh timestamped sample folder. Wait for the success message, inspect orientation/materials/collision, and only then run the documented full command with `preflight_report=sample_report` and `visual_review_approved=True`. Never manufacture a sample report or bypass preflight.

The reported tangent/bi-normal warnings on carton/tile meshes remain visual-review items; they did not cause the shown exception. This patch has local syntax/contract/regression checks; a successful Unreal rerun is still required.

Reference: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/CollisionResponseType?application_version=5.7
