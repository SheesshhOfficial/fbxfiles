"""Verify all ASCII relative FBX texture references; supports nested scanned maps."""
import pathlib,re,json
ROOT=pathlib.Path(__file__).resolve().parents[1];results=[]
manifest=json.loads((ROOT/'unreal/environment_manifest.json').read_text())
for item in manifest['assets']:
 f=ROOT/item['fbx']
 paths=sorted(set(x.decode() for x in re.findall(rb'(?:\.\./)+textures/[A-Za-z0-9_./ -]+\.(?:png|jpe?g|exr|tiff?)',f.read_bytes(),re.I)))
 results.append({'fbx':f.name,'relative_texture_paths':paths,'all_paths_resolve':all((f.parent/p).is_file() for p in paths)})
out={'source_sha256':manifest['source_sha256'],'fbx_count':len(results),'all_paths_resolve':all(x['all_paths_resolve'] for x in results),'shared_texture_dependency':'Preserve complete textures tree, including nested realistic and derived folders. Images are not embedded.','files':results}
(ROOT/'qa/environment_texture_paths.json').write_text(json.dumps(out,indent=2));print(out['all_paths_resolve'])
