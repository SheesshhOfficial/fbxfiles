"""Run this file with Unreal Tools > Execute Python Script. PREFLIGHT ONLY."""
from pathlib import Path
import importlib.util
import sys
fixture_state = r'C:\Art\Evergreen_Native_Run_01\run_state.json'
fixture_folder = Path(r'C:\Art\Evergreen_Fixture_Lighting')
spec = importlib.util.spec_from_file_location('evergreen_fixture_patch_isolated',fixture_folder/'fixture_point_patch.py')
fixture_patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_patch)
fixture_layout = str(fixture_folder/'fixture_point_layout_v1.json')
fixture_dry_run = fixture_patch.run(fixture_state,fixture_layout)
print('PREFLIGHT ONLY. Inspect removed identities, retained manual lights and proposed points. No map changes.')
