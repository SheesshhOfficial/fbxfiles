"""Restart-safe, read-only sample plan. Never executes the patch automatically."""
import sys
import importlib
from pathlib import Path
package = r"C:\Art\Evergreen_Market_Unreal_Handoff"
patch = r"C:\Art\Evergreen_Market_Normals_Patch"
source = Path(package) / "source"
sys.path.insert(0, str(source))
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep
import setup_market_normals as en
for module in (em, ec, ep, en):
    if Path(module.__file__).resolve().parent != source.resolve():
        raise RuntimeError("Different helper folder already loaded. Restart Unreal and retry: " + str(module.__file__))
    importlib.reload(module)
normals_plan = en.run_current(package, patch)
print("DRY RUN ONLY. Review the sample plan before making a backed-up copy.")
