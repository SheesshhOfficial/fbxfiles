"""Finalize catalogs/checksums/ZIP after successful Blender and contract QA."""
from pathlib import Path
import json,csv,hashlib,zipfile,sys
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'manifest.json').read_text());qa=json.loads((ROOT/'qa/blender_roundtrip.json').read_text());assert qa['status']=='passed'
assets=m['assets'];props=[a for a in assets if a['category']=='disguise_candidate']
with (ROOT/'docs/PROP_ASSET_LIST.csv').open('w',newline='') as f:
 fields=['AssetId','Name','RecommendedInitially','DisguiseTier','SceneCopies','SizeX_cm','SizeY_cm','SizeZ_cm','FBX','Collision']
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for a in sorted(props,key=lambda a:(a['disguise_tier'],a['name'],a['asset_id'])):
  w.writerow(dict(AssetId=a['asset_id'],Name=a['name'],RecommendedInitially=a['disguise_tier']=='default',DisguiseTier=a['disguise_tier'],SceneCopies=a['instance_count'],SizeX_cm=a['bounds_cm'][0],SizeY_cm=a['bounds_cm'][1],SizeZ_cm=a['bounds_cm'][2],FBX=a['fbx_path'],Collision=a['collision']['strategy']))
with (ROOT/'docs/ALL_ASSETS.csv').open('w',newline='') as f:
 fields=['AssetId','Name','Category','DisguiseTier','SceneCopies','Triangles','Materials','FBX'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for a in sorted(assets,key=lambda a:a['asset_id']):w.writerow(dict(AssetId=a['asset_id'],Name=a['name'],Category=a['category'],DisguiseTier=a['disguise_tier'],SceneCopies=a['instance_count'],Triangles=a['triangles'],Materials=';'.join(a['materials']),FBX=a['fbx_path']))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[p for p in ROOT.rglob('*') if p.is_file() and not any(t in p.parts for t in ['__pycache__']) and p.suffix not in ['.log','.blend1'] and p.name not in ['CHECKSUMS.json','package_result.json']]
(ROOT/'CHECKSUMS.json').write_text(json.dumps({str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)},indent=2));paths.append(ROOT/'CHECKSUMS.json')
zip_path=ROOT.parent/'Evergreen_Market_Unreal_Handoff.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(paths):z.write(p,'Evergreen_Market_Unreal_Handoff/'+str(p.relative_to(ROOT)))
with zipfile.ZipFile(zip_path) as z:assert z.testzip() is None
print(json.dumps({'zip':str(zip_path),'bytes':zip_path.stat().st_size,'sha256':sha(zip_path),'assets':len(assets),'prop_asset_variants':len(props),'placements':len(m['placements']),'archive_verified':True},indent=2))
