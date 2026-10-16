"""Fresh import preflight only. Explicit state path; never chooses newest reports."""
import sys
import importlib
from pathlib import Path
package=r'C:\Art\Evergreen_Market_Unreal_Handoff'
patch=r'C:\Art\Evergreen_Market_Normals_Patch'
fresh_work=r'C:\Art\Evergreen_Fresh_Run'
fresh_state=str(Path(fresh_work)/'run_state.json')
source=(Path(fresh_work)/'CorrectedPackage'/'source') if Path(fresh_state).is_file() else (Path(package)/'source')
sys.path.insert(0,str(source))
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep
import setup_market_normals as en
import fresh_market_start as fw
for module in (em,ec,ep,en,fw):
    if Path(module.__file__).resolve().parent!=source.resolve():
        raise RuntimeError('Different helper folder already loaded. Restart Unreal and rerun this starter: '+str(module.__file__))
    importlib.reload(module)
if Path(fresh_state).is_file():
    fw.step(fresh_state)
else:
    fw.start(package,patch,fresh_work)
print('PREFLIGHT ONLY. No imports or scene changes performed.')
