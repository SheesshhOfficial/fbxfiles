# Recover the existing sample lights

The diagnostic identified the directional Sun actor at scale 2.5 instead of the intended scale 1. Its location/rotation and the ten point-light transforms are correct. This scoped recovery reuses all eleven tagged lights; it does not create/delete lights or reimport assets.

The corrected helper verifies the exact failed sample report, all eleven keys/classes/settings, and sample geometry. It changes only the permitted Sun transform, saves and reloads, and verifies everything again. Only after success does the wrapper migrate the preview-helper hash and mark the lighting step complete. The failed report remains unchanged. Original run-state bytes and preview helper are backed up in a uniquely named LightingRecovery folder beside run_state.json.

## Commands
1. Extract the recovery bundle to C:\Art\Evergreen_Lighting_Recovery. Keep all files together. Do not overwrite the original or CorrectedPackage helper folders yourself.
2. Open the failed sample map containing all eleven lights. Save it and all manual changes, stop Play, and back up the project.
3. In Output Log → Python:

```python
exec(open(r"C:\Art\Evergreen_Lighting_Recovery\Start_Lighting_Recovery.py", encoding="utf-8").read())
```

This restores fw and fresh_state from the exact prepared run and prints the read-only light diagnostic.

4. After reviewing the diagnostic:

```python
lighting_report = lr.run(fresh_state, execute=True, backup_confirmed=True)
```

5. Inspect the lit sample. Find PaperShoppingBag, Checkout_base, Impulse_display and ShippingCarton_Floor in the Outliner and press F. Only if their geometry/materials look correct:

```python
fw.finish(fresh_state, execute=True, backup_confirmed=True, visual_review_approved=True)
```

After the full/collision/pilot stages succeed, optional final preview:

```python
fw.preview(fresh_state, execute=True, backup_confirmed=True)
```

The wrapper makes the corrected preview helper available to later fw.preview calls in the current session. After a restart, restore fw and fresh_state with:

```python
exec(open(r"C:\Art\Evergreen_Market_Unreal_Handoff\source\Start_Fresh_Market.py", encoding="utf-8").read())
```

The prepared helper snapshot and state now agree. Do not rerun Start_Lighting_Recovery after a successful migration; it intentionally accepts only the original failed state.

If recovery stops, keep its first error and the LightingRecovery backup/migration report. Do not rerun the fresh importer, edit state manually, or replace helper hashes. A rare interruption between helper installation and state commit requires scoped inspection; the verified backups allow recovery without guessing. This tool has local/mock validation only, not execution in your Unreal editor.
