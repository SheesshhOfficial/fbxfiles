"""Read-only, exact-current-map repair preflight. Never executes automatically."""
import sys
import importlib
from pathlib import Path
package=r'C:\Art\Evergreen_Market_Unreal_Handoff'
source=Path(package)/'source'
sys.path.insert(0,str(source))
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep
import setup_market_normals as en
import repair_pilot_collision as er
for module in (em,ec,ep,en,er):
    if Path(module.__file__).resolve().parent!=source.resolve():
        raise RuntimeError('Wrong helper folder loaded. Restart Unreal and retry: '+str(module.__file__))
    importlib.reload(module)
pilot_collision_plan=er.run_current(package)
print('DRY RUN ONLY. Save your current map and back up before executing the repair.')
