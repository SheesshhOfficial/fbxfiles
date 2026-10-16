"""Rebuild the approved-scope pantry vertical slice from its authored source steps.
Usage: python rebuild_slice.py --blender /path/to/blender [--render]
Existing vertical-slice outputs in this folder are replaced; other projects are untouched.
"""
from pathlib import Path
import argparse,subprocess
p=argparse.ArgumentParser();p.add_argument('--blender',default='/usr/bin/blender');p.add_argument('--render',action='store_true');a=p.parse_args();root=Path(__file__).resolve().parent
for script in ['build_premium_slice.py','finalize_scene.py','complete_source_contract.py','refine_product_composition.py','pack_relative_assets.py']:
 subprocess.run([a.blender,'-b','-t','8','--python',str(root/script)],check=True)
if a.render:subprocess.run([a.blender,'-b','-t','8','--python',str(root/'render_slice.py')],check=True)
