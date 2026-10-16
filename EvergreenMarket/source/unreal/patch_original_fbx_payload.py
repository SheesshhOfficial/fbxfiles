"""Exact-value FBX winding/normal/UV-corner patch using Blender's bundled FBX codec.
Avoids lossy Blender custom-normal re-encoding, including degenerate bevel normal fans.
blender -b --python patch_original_fbx_payload.py -- ORIGINAL_HANDOFF PATCH_ROOT
"""
import bpy,sys,json,hashlib,array,ast,collections,math,copy
from pathlib import Path
from mathutils import Vector
from io_scene_fbx import parse_fbx,encode_bin
args=sys.argv[sys.argv.index('--')+1:];ORIGINAL=Path(args[0]).resolve();ROOT=Path(args[1]).resolve()
assert ORIGINAL != ROOT, 'Use a separate patch output folder; never overwrite original source files'
sys.path.insert(0,str(ROOT/'source'))
from classify_closed_shells import analyze

def child(e,name):return next(x for x in e.elems if x.id==name)
def children(e,name):return [x for x in e.elems if x.id==name]
def prop(e,name):return child(e,name).props[0]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,separators=(',',':')).encode()).hexdigest()
def decoded(e):
    def val(v):
        if isinstance(v,bytes):return ('bytes',v.hex())
        if isinstance(v,array.array):return ('array',v.typecode,list(v))
        return v
    return [e.id.hex(),list(e.props_type),[val(p) for p in e.props],[decoded(c) for c in e.elems]]

def polys(g):
    faces=[];loops=[];f=[];ls=[]
    for i,v in enumerate(prop(g,b'PolygonVertexIndex')):
        f.append(v if v>=0 else -v-1);ls.append(i)
        if v<0:faces.append(f);loops.append(ls);f=[];ls=[]
    assert not f
    return faces,loops

def shell_info(g):
    vs=prop(g,b'Vertices');faces,loops=polys(g)
    me=bpy.data.meshes.new('QA');me.from_pydata(list(zip(vs[0::3],vs[1::3],vs[2::3])),[],faces);me.update()
    s=analyze(me);bpy.data.meshes.remove(me)
    return s

def snapshot(g):
    faces,loops=polys(g);data={}
    data['vertices']=list(prop(g,b'Vertices'));data['faces']=faces;data['loops']=loops
    data['normals']=[];data['uvs']=[]
    for lay in children(g,b'LayerElementNormal'):
        assert prop(lay,b'MappingInformationType')==b'ByPolygonVertex' and prop(lay,b'ReferenceInformationType')==b'IndexToDirect'
        arr=prop(lay,b'Normals');idx=prop(lay,b'NormalsIndex')
        data['normals'].append([[tuple(arr[3*idx[li]:3*idx[li]+3]) for li in ls] for ls in loops])
    for lay in children(g,b'LayerElementSmoothing'):
        assert prop(lay,b'MappingInformationType') in {b'ByPolygon',b'ByEdge',b'AllSame'}, 'Unsupported smoothing mapping'
    for lay in children(g,b'LayerElementMaterial'):
        assert prop(lay,b'MappingInformationType') in {b'ByPolygon',b'AllSame'}, 'Unsupported material mapping'
    for lay in children(g,b'LayerElementUV'):
        assert prop(lay,b'MappingInformationType')==b'ByPolygonVertex' and prop(lay,b'ReferenceInformationType')==b'IndexToDirect'
        arr=prop(lay,b'UV');idx=prop(lay,b'UVIndex')
        data['uvs'].append([[tuple(arr[2*idx[li]:2*idx[li]+2]) for li in ls] for ls in loops])
    data['materials']=[decoded(l) for l in children(g,b'LayerElementMaterial')]
    data['smoothing']=[decoded(l) for l in children(g,b'LayerElementSmoothing')]
    data['edges']=[tuple(sorted((faces[pi][j],faces[pi][(j+1)%len(faces[pi])]))) for li in prop(g,b'Edges') for pi,ls in enumerate(loops) for j,l in enumerate(ls) if l==li] if len(loops)<500 else None
    return data

def patch_geometry(g):
    faces,loops=polys(g);s=shell_info(g);flip={pi for x in s if x['eligible_for_flip'] for pi in x['polygon_indices']}
    if not flip:return dict(changed=False,shells=s),False
    corner_map=[];newfaces=[];newindices=[];old_edge_pairs={};new_edge_loops={}
    for pi,(f,ls) in enumerate(zip(faces,loops)):
        for j,li in enumerate(ls):old_edge_pairs[li]=tuple(sorted((f[j],f[(j+1)%len(f)])))
        order=list(reversed(range(len(f)))) if pi in flip else list(range(len(f)))
        nf=[f[j] for j in order];newfaces.append(nf);corner_map.extend(ls[j] for j in order)
        newindices.extend(nf[:-1]+[-nf[-1]-1])
        for j,li in enumerate(ls):new_edge_loops.setdefault(tuple(sorted((nf[j],nf[(j+1)%len(nf)]))),li)
    child(g,b'PolygonVertexIndex').props[0]=array.array('i',newindices)
    child(g,b'Edges').props[0]=array.array('i',[new_edge_loops[old_edge_pairs[li]] for li in prop(g,b'Edges')])
    flipped_old_loops={li for pi in flip for li in loops[pi]}
    allowed={b'LayerElementNormal',b'LayerElementUV',b'LayerElementSmoothing',b'LayerElementMaterial'}
    assert all(not e.id.startswith(b'LayerElement') or e.id in allowed for e in g.elems), 'Unrecognized corner attribute: refusing to lose data'
    for lay in children(g,b'LayerElementUV'):
        assert prop(lay,b'MappingInformationType')==b'ByPolygonVertex';assert prop(lay,b'ReferenceInformationType')==b'IndexToDirect'
        old=prop(lay,b'UVIndex');child(lay,b'UVIndex').props[0]=array.array('i',[old[li] for li in corner_map])
    for lay in children(g,b'LayerElementNormal'):
        assert prop(lay,b'MappingInformationType')==b'ByPolygonVertex';assert prop(lay,b'ReferenceInformationType')==b'IndexToDirect'
        old=prop(lay,b'NormalsIndex');norm=list(prop(lay,b'Normals'));neg={};idx=[]
        for li in corner_map:
            ni=old[li]
            if li in flipped_old_loops:
                if ni not in neg:
                    neg[ni]=len(norm)//3;norm.extend(-q for q in norm[ni*3:ni*3+3])
                idx.append(neg[ni])
            else:idx.append(ni)
        child(lay,b'Normals').props[0]=array.array('d',norm);child(lay,b'NormalsIndex').props[0]=array.array('i',idx)
    return dict(changed=True,shells=s,flipped_polygons=sorted(flip)),True

def verify_payload(og,cg):
    o=snapshot(og);c=snapshot(cg);shells=shell_info(og);after=shell_info(cg);flip={pi for s in shells if s['eligible_for_flip'] for pi in s['polygon_indices']}
    assert o['vertices']==c['vertices'];assert len(o['faces'])==len(c['faces']);assert o['materials']==c['materials'];assert o['smoothing']==c['smoothing'];assert len(o['uvs'])==len(c['uvs']);assert len(o['normals'])==len(c['normals'])
    canon_uvs_o=[];canon_uvs_c=[];canon_normal_expected=[];canon_normal_actual=[]
    for pi,(of,cf) in enumerate(zip(o['faces'],c['faces'])):
        assert cf==(list(reversed(of)) if pi in flip else of)
        for ou,cu in zip(o['uvs'],c['uvs']):
            a=sorted(zip(of,ou[pi]));b=sorted(zip(cf,cu[pi]));assert a==b;canon_uvs_o.append(a);canon_uvs_c.append(b)
        for on,cn in zip(o['normals'],c['normals']):
            expected=sorted((vi,tuple(-q for q in n) if pi in flip else n) for vi,n in zip(of,on[pi]));actual=sorted(zip(cf,cn[pi]));assert expected==actual
            canon_normal_expected.append(expected);canon_normal_actual.append(actual)
    # Exact FBX edge connectivity preserved even though representative corner index changes.
    def edge_pairs(g):
        fs,ls=polys(g);byloop={li:tuple(sorted((f[j],f[(j+1)%len(f)]))) for f,l in zip(fs,ls) for j,li in enumerate(l)}
        return [byloop[i] for i in prop(g,b'Edges')]
    assert edge_pairs(og)==edge_pairs(cg)
    for bs,as_ in zip(shells,after):
        expected=-bs['signed_volume_m3'] if bs['eligible_for_flip'] else bs['signed_volume_m3'];assert abs(as_['signed_volume_m3']-expected)<=max(1e-12,abs(expected)*1e-6);assert not as_['eligible_for_flip']
    ih=dict(coordinates_sha256=digest(o['vertices']),geometry_membership_sha256=digest([sorted(f) for f in o['faces']]),uv_corner_association_sha256=digest(canon_uvs_o),material_assignments_sha256=digest(o['materials']),smoothing_sha256=digest(o['smoothing']),edge_connectivity_sha256=digest(edge_pairs(og)),expected_corrected_normal_associations_sha256=digest(canon_normal_expected),actual_corrected_normal_associations_sha256=digest(canon_normal_actual))
    return dict(passed=True,vertices=len(o['vertices'])//3,polygons=len(o['faces']),flipped_polygons=len(flip),inward_closed_shells_fixed=sum(s['eligible_for_flip'] for s in shells),positive_closed_shells_after=sum(s['closed'] and s['signed_volume_m3']>s['volume_threshold_m3'] for s in after),open_shells_preserved=sum(not s['closed'] for s in shells),max_coordinate_delta_m=0,max_uv_corner_delta=0,max_normal_vector_delta_from_expected=0,exact_material_assignments_preserved=True,exact_edge_connectivity_preserved=True,invariant_hashes=ih)

methods={ord(k):v for k,v in {'B':'add_bool','C':'add_char','Z':'add_int8','Y':'add_int16','I':'add_int32','L':'add_int64','F':'add_float32','D':'add_float64','R':'add_bytes','S':'add_string','i':'add_int32_array','l':'add_int64_array','f':'add_float32_array','d':'add_float64_array','b':'add_bool_array','c':'add_byte_array'}.items()}
def enc(e):
    out=encode_bin.FBXElem(e.id)
    for typ,p in zip(e.props_type,e.props):getattr(out,methods[typ])(p)
    out.elems=[enc(c) for c in e.elems]
    return out
# Preserve original header/metadata as well as scene data. Original Blender exports already use its fixed timestamp.
encode_bin._write_timedate_hack=lambda e:None
manifest=json.loads((ROOT/'patch_manifest.json').read_text());rows=[]
assert sha(ORIGINAL/'manifest.json') == manifest['original_manifest_sha256'], 'Wrong original handoff manifest'
for idx,rec in enumerate(manifest['assets']):
    assert sha(ORIGINAL/rec['fbx_path']) == rec['original_file_sha256'], 'Original FBX does not match approved baseline'
    original,version=parse_fbx.parse(str(ORIGINAL/rec['fbx_path']));corrected=copy.deepcopy(original)
    ogs=children(child(original,b'Objects'),b'Geometry');cgs=children(child(corrected,b'Objects'),b'Geometry');assert len(ogs)==len(cgs)
    changed=False
    for g in cgs:
        info,ch=patch_geometry(g);changed|=ch
    assert changed
    encode_bin.write(str(ROOT/rec['fbx_path']),enc(corrected),version)
    reread,v=parse_fbx.parse(str(ROOT/rec['fbx_path']));assert v==version
    rgs=children(child(reread,b'Objects'),b'Geometry');results=[]
    for og,rg in zip(ogs,rgs):results.append(verify_payload(og,rg))
    # Everything except explicitly repaired per-geometry payloads must match the original tree exactly.
    untouched_o=copy.deepcopy(original);untouched_r=copy.deepcopy(reread)
    for t in [untouched_o,untouched_r]:
        for g in children(child(t,b'Objects'),b'Geometry'):
            g.elems[:]=[e for e in g.elems if e.id not in {b'PolygonVertexIndex',b'Edges'}]
            for lay in children(g,b'LayerElementNormal'):
                lay.elems[:]=[e for e in lay.elems if e.id not in {b'Normals',b'NormalsIndex'}]
            for lay in children(g,b'LayerElementUV'):
                lay.elems[:]=[e for e in lay.elems if e.id != b'UVIndex']
    assert decoded(untouched_o)==decoded(untouched_r),'Unrelated FBX content changed'
    row=dict(asset_id=rec['asset_id'],passed=True,all_nonrepaired_fbx_data_exactly_preserved=True,objects=results);rows.append(row)
    rec['file_sha256']=sha(ROOT/rec['fbx_path']);rec['exact_fbx_payload_verification']=results;rec.pop('native_verification',None)
    (ROOT/'qa/fbx_exact_payload.json').write_text(json.dumps(dict(passed=True,assets_verified=len(rows),assets_expected=len(manifest['assets']),complete=len(rows)==len(manifest['assets']),assets=rows),indent=2))
    if idx<6 or idx%30==0:print('EXACT FBX VERIFIED',idx+1,len(manifest['assets']),rec['asset_id'],flush=True)
manifest['method']='Schema-aware patch of original binary FBX. Reverse only eligible shell polygon order, remap existing UV corner indices and edge references, and negate original float64 normal vectors only for flipped corners. All other scene payloads preserved exactly.'
manifest['summary']['collision_only_assets']=sum(a['collision_box_winding_fixed'] and not a['render_changed'] for a in manifest['assets'])
manifest['native_blend_note']='The winding-corrected native copy is excluded from final deliverables because Blender 4.3 compressed custom-normal re-encoding on pre-existing degenerate bevel faces did not meet exact preservation. The corrected FBXs retain the original normals exactly except for required sign inversion.'
manifest.pop('corrected_blend_path',None);manifest.pop('corrected_blend_sha256',None)
(ROOT/'patch_manifest.json').write_text(json.dumps(manifest,indent=2))
print('EXACT PAYLOAD PATCH COMPLETE',len(rows),flush=True)
