"""Read-only diagnostic for the exact failed fresh-lighting state. No automatic repair."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
fresh_state=r'C:\Art\Evergreen_Fresh_Run\run_state.json'
recovery_folder=Path(r'C:\Art\Evergreen_Lighting_Recovery')
state=json.loads(Path(fresh_state).read_text(encoding='utf-8'))
source=Path(state['merged_package'])/'source'

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise RuntimeError('Cannot load helper: '+str(path))
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

# Load the exact unchanged run snapshot in dependency order, regardless of older
# module locations from prior editor sessions. Verify every file BEFORE execution.
names=('import_supermarket_unreal','setup_market_collision','setup_prop_actor_pilot','setup_market_normals','fresh_market_start')
for name in names:
    file=source/(name+'.py')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=state['helper_hashes'].get(name+'.py'):
        raise RuntimeError('Run snapshot changed; stop: '+str(file))
sys.path.insert(0,str(source))
for name in names:globals()[{'fresh_market_start':'fw'}.get(name,name)]=_load(name,source/(name+'.py'))
lr=_load('recover_fresh_lighting',recovery_folder/'recover_fresh_lighting.py')
lighting_diagnostic=lr.run(fresh_state)
print('DIAGNOSTIC ONLY. Existing lights, files and run state were not changed.')
