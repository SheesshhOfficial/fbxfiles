"""Preserve exact source corner normals in FBX without Blender's packed-normal encoding.
Uses Blender's installed FBX parser/encoder. Geometry, UVs and material data retained.
"""
from io_scene_fbx import parse_fbx,encode_bin
import array,math

def replace_corner_normals(path,asset_name,normals,force_smooth=True):
 tree,version=parse_fbx.parse(str(path))
 def child(e,key):return next((c for c in e.elems if c.id==key),None)
 objects=child(tree,b'Objects')
 geo=next(e for e in objects.elems if e.id==b'Geometry' and e.props[1].split(b'\x00')[0].decode()==asset_name)
 indices=child(geo,b'PolygonVertexIndex').props[0]
 assert len(indices)==len(normals),'Corner count mismatch before FBX normal replacement'
 layer=child(geo,b'LayerElementNormal');assert child(layer,b'MappingInformationType').props[0]==b'ByPolygonVertex'
 def replace(e,values,typechar):e.props[:]=[values];e.props_type[:]=bytes(typechar,'ascii')
 replace(child(layer,b'Normals'),array.array('d',(v for n in normals for v in n)),'d')
 index=child(layer,b'NormalsIndex')
 if index:replace(index,array.array('i',range(len(normals))),'i')
 else:
  # Direct mapping needs no index array.
  assert child(layer,b'ReferenceInformationType').props[0]==b'Direct'
 smooth=child(geo,b'LayerElementSmoothing')
 if force_smooth and smooth:
  assert child(smooth,b'MappingInformationType').props[0]==b'ByPolygon'
  values=child(smooth,b'Smoothing');replace(values,array.array('i',[1]*sum(i<0 for i in indices)),'i')
 methods={'B':'add_bool','C':'add_char','Z':'add_int8','Y':'add_int16','I':'add_int32','L':'add_int64','F':'add_float32','D':'add_float64','R':'add_bytes','S':'add_string','i':'add_int32_array','l':'add_int64_array','f':'add_float32_array','d':'add_float64_array','b':'add_bool_array','c':'add_byte_array'}
 def convert(e):
  out=encode_bin.FBXElem(e.id)
  for kind,value in zip(e.props_type,e.props):getattr(out,methods[chr(kind)])(value)
  out.elems=[convert(c) for c in e.elems];return out
 encode_bin.write(str(path),convert(tree),version)
 return {'corner_count':len(normals),'method':'Exact inverse-transposed source per-corner normal array written directly to FBX; explicit smooth groups retain custom normals.'}
