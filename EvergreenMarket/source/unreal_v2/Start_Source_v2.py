"""Edit these two absolute paths. Executing this file performs PREFLIGHT ONLY."""
import sys
import importlib
from pathlib import Path
package=r'C:\Art\Evergreen_Market_Source_v2'
fresh_work=r'C:\Art\Evergreen_Native_Run_01'
fresh_state=str(Path(fresh_work)/'run_state.json')
source=(Path(fresh_work)/'NativePackage'/'source'/'unreal') if Path(fresh_state).is_file() else Path(package)/'source'/'unreal'
sys.path.insert(0,str(source))
for name in ('import_supermarket_unreal','setup_market_collision','setup_prop_actor_pilot','fresh_preview_setup','fresh_market_source_v2'):
    module=importlib.import_module(name)
    if Path(module.__file__).resolve().parent!=source.resolve():
        raise RuntimeError('Different helper folder already loaded. Restart Unreal before continuing: '+str(module.__file__))
    importlib.reload(module)
import fresh_market_source_v2 as fw
if Path(fresh_state).is_file():fw.step(fresh_state)
else:fw.start(package,fresh_work)
print('PREFLIGHT ONLY: no import, asset, map or Blueprint changes.')
