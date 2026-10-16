"""Safe with plain exec(open(...).read()); dry-run only, no __file__ assumption."""
from pathlib import Path
import importlib.util
prop_batch_folder = Path(r'C:\Art\Evergreen_Prop_Batch')
prop_batch_spec = importlib.util.spec_from_file_location('evergreen_prop_batch_isolated', prop_batch_folder/'prop_batch_patch.py')
prop_batch = importlib.util.module_from_spec(prop_batch_spec)
prop_batch_spec.loader.exec_module(prop_batch)
prop_batch_dry_run = prop_batch.run(str(prop_batch_folder))
print('PREFLIGHT ONLY: no map changes. Review the 16 selections; execute only after backup.')
