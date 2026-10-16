"""Derive ceiling-light locations from source-exported fixture placements."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'evergreen_source_v2'
OUT = ROOT / 'fixture_lighting_work'
manifest_path = SOURCE / 'manifest.json'
m = json.loads(manifest_path.read_text())
assets = {a['asset_id']: a for a in m['assets']}
diffusers = [p for p in m['placements'] if assets[p['asset_id']]['name'] == 'Opal LED diffuser']
housings = [p for p in m['placements'] if assets[p['asset_id']]['name'] == 'Suspended LED housing']
assert len(diffusers) == len(housings) == 25
lights = []
for i, p in enumerate(sorted(diffusers, key=lambda p: (p['location_cm'][0], -p['location_cm'][1])), 1):
    x,y,z = p['location_cm']
    assert p['scale'] == [1.0,1.0,1.0]
    assert max(abs(v) for v in p['rotation_deg']) < 1e-5
    matching = [h for h in housings if abs(h['location_cm'][0]-x)<.001 and abs(h['location_cm'][1]-y)<.001]
    assert len(matching) == 1
    lights.append(dict(key=f'Fixture_{i:02d}', actor='PointLight', component='PointLightComponent',
        location_cm=[x,y,430.0], rotation_degrees_pitch_yaw_roll=[0,0,0], scale=[1,1,1],
        intensity=3000.0, intensity_unit='lumens', attenuation_radius_cm=900.0,
        source_radius_cm=2.0, soft_source_radius_cm=0.0, source_length_cm=0.0,
        use_inverse_squared_falloff=True, color_linear_rgba=[1,1,1,1],
        mobility='Movable', cast_shadows=True,
        source_fixture_instance_id=p['instance_id'], source_fixture_asset_id=p['asset_id'],
        source_fixture_names=p['source_names'], source_collection=p['source_collection'],
        source_fixture_bottom_cm=p['location_cm'],
        source_fixture_center_cm=[x,y,z+assets[p['asset_id']]['bounds_cm'][2]/2],
        source_position_m=[x/100.0,-y/100.0,z/100.0],
        fixture_point_position_m=[x/100.0,-y/100.0,4.3],
        source_fixture_dimensions_cm=assets[p['asset_id']]['bounds_cm'],
        source_housing_instance_id=matching[0]['instance_id'],
        emitter_clearance_below_diffuser_cm=round(z-430.0,6)))
# Exterior fixture coverage, derived from physical source positions and extents.
for role, prefix, lumens, radius in [('Canopy linear light','Canopy',250.0,500.0), ('Exterior wall lamp','ExteriorWall',1000.0,600.0)]:
    fixtures = sorted([p for p in m['placements'] if assets[p['asset_id']]['name'] == role],key=lambda p: tuple(p['location_cm']))
    assert len(fixtures) == (15 if prefix == 'Canopy' else 2)
    for i,p in enumerate(fixtures,1):
        x,y,z=p['location_cm']; dims=assets[p['asset_id']]['bounds_cm']
        assert p['scale']==[1.0,1.0,1.0] and max(abs(v) for v in p['rotation_deg'])<1e-5
        center=[x,y,z+dims[2]/2]
        point=[x,y,z-4.5] if prefix=='Canopy' else [x+dims[0]/2+5.0,y,center[2]]
        lights.append(dict(key=f'{prefix}_{i:02d}',actor='PointLight',component='PointLightComponent',
            location_cm=point,rotation_degrees_pitch_yaw_roll=[0,0,0],scale=[1,1,1],
            intensity=lumens,intensity_unit='lumens',attenuation_radius_cm=radius,
            source_radius_cm=2.0,soft_source_radius_cm=0.0,source_length_cm=0.0,
            use_inverse_squared_falloff=True,color_linear_rgba=[1,1,1,1],mobility='Movable',cast_shadows=True,
            source_fixture_instance_id=p['instance_id'],source_fixture_asset_id=p['asset_id'],
            source_fixture_names=p['source_names'],source_collection=p['source_collection'],
            source_fixture_bottom_cm=p['location_cm'],source_fixture_center_cm=center,
            source_fixture_dimensions_cm=dims,source_position_m=[x/100,-y/100,z/100],
            fixture_point_position_m=[point[0]/100,-point[1]/100,point[2]/100],
            placement_note='4.5 cm below canopy underside' if prefix=='Canopy' else '5 cm beyond outward +X face; at physical lamp center height'))
layout = dict(schema='evergreen-fixture-point-layout-v1',
    purpose='One point per actual ceiling, canopy, and exterior wall fixture; initial untested settings.',
    coordinate_system=m['coordinate_system'],
    source_manifest='evergreen_source_v2/manifest.json',
    source_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    source_blend_sha256=m['source_blend_sha256'],
    source_fixture_count=len(lights), fixture_role_counts=dict(ceiling=25,canopy=15,exterior_wall=2),
    source_evidence='source/blender/build_supermarket.py lines 200, 216-223, 509; exported fixture placements.',
    placement_policy='Ceiling: source X/Y and Z430 cm, 4.25 cm below diffuser. Canopy: source X/Y and 4.5 cm below underside. Wall: 5 cm beyond +X outer face at mesh-center height. No fill grid synthesized.',
    excluded_fixture_roles=['Case vertical LED: 15 refrigerated-case accents remain emissive; not separate point-light fixtures in this patch'],
    directional_lights_allowed=False, skylights_allowed=False, rect_lights_allowed=False,
    unreal_runtime_tested=False,
    tuning_note='Ceiling 3000 lumens/900 cm, canopy 250 lumens/500 cm, wall 1000 lumens/600 cm are initial neutral preview settings, not a photometric or runtime validation. Keep shadows for shelving and wall occlusion; profile the 42 movable shadow-casting points in the target engine. Do not add overlapping fill lights or disable all shadows to mask performance problems.',
    lights=lights)
assert len({tuple(l['location_cm']) for l in lights}) == 42
(OUT/'fixture_point_layout_v1.json').write_text(json.dumps(layout,indent=2)+'\n')
print(json.dumps({'light_count':len(lights),'x_cm':sorted({l['location_cm'][0] for l in lights}), 'y_cm':sorted({l['location_cm'][1] for l in lights}), 'z_cm':sorted({l['location_cm'][2] for l in lights}),'ceiling_housing_pairs':25,'unreal_runtime_tested':False},indent=2))
