"""Reviewed import entrypoint for UE5 Editor Python. NOT executed in Unreal.
Run by adding this directory to sys.path and importing import_carnival, then
import_carnival.import_carnival(). Creates /Game/MoonfallCarnivalV2/Maps/MoonfallCarnival.
Refuses existing target map and unsaved current map changes. Never deletes actors.
Inspect and save the final level manually. Source light estimates/starts included; add project gameplay and tune lighting.
"""
import os,sys

def import_carnival(root=None):
 root=os.path.abspath(root or os.path.dirname(__file__))
 if root not in sys.path:sys.path.insert(0,root)
 from import_environment import import_environment
 from import_props import import_props
 environment=import_environment(root=root,create_level=True,allow_existing=False)
 props=import_props(root=root)
 scene_metadata={'status':'manifest absent'}
 if os.path.isfile(os.path.join(root,'scene_metadata.json')):
  from import_scene_metadata import import_scene_metadata
  scene_metadata=import_scene_metadata(root=root)
 result={'environment':environment,'props':props,'scene_metadata':scene_metadata,'unreal_runtime_verified':False}
 print(result)
 return result

if __name__=='__main__':import_carnival()
