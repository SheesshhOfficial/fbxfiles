"""Synthetic geometry tests; creates no external source artifacts."""
import importlib.util
import json
from pathlib import Path

import bpy
import bmesh

path = Path(__file__).with_name("audit_blender_slice.py")
spec = importlib.util.spec_from_file_location("slice_audit", path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
results = []


def cube(name, inward=False, offset=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2)
    for v in bm.verts:
        v.co.x += offset[0]
        v.co.y += offset[1]
        v.co.z += offset[2]
    if inward:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def check(name, condition):
    assert condition, name
    results.append({"test": name, "passed": True})


positive = cube("positive")
g = audit.mesh_geometry(positive, convex=True)
check("outward_closed_cube_positive_volume", len(g["shells"]) == 1 and g["shells"][0]["closed"] and abs(g["shells"][0]["signed_volume"] - 8) < 1e-6)
check("outward_cube_convex", g["convex_violation_count"] == 0)

negative = cube("negative", inward=True)
g = audit.mesh_geometry(negative, convex=True)
check("inward_cube_negative_volume", g["shells"][0]["orientation"] == "negative" and abs(g["shells"][0]["signed_volume"] + 8) < 1e-6)
check("inward_cube_fails_outward_halfspaces", g["convex_violation_count"] > 0)

verts = [tuple(v.co) for v in positive.vertices] + [(v.co.x + 4, v.co.y, v.co.z) for v in negative.vertices]
faces = [tuple(p.vertices) for p in positive.polygons] + [tuple(i + 8 for i in p.vertices) for p in negative.polygons]
mixed = bpy.data.meshes.new("mixed")
mixed.from_pydata(verts, [], faces)
mixed.update()
g = audit.mesh_geometry(mixed, convex=False)
check("inward_shell_not_hidden_by_aggregate", len(g["shells"]) == 2 and sorted(s["orientation"] for s in g["shells"]) == ["negative", "positive"])

plane = bpy.data.meshes.new("intentional_label_plane")
plane.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2, 3)])
plane.update()
g = audit.mesh_geometry(plane, convex=False)
check("open_label_distinguished_from_inward_solid", not g["shells"][0]["closed"] and g["shells"][0]["orientation"] == "zero" and g["shells"][0]["boundary_edges"] == 4)

bad = cube("nonconvex")
bad.vertices[0].co *= 0.1
bad.update()
g = audit.mesh_geometry(bad, convex=True)
check("dented_hull_rejected", g["convex_violation_count"] > 0)

far = cube("far_away", offset=(100000, 100000, 100000))
g = audit.mesh_geometry(far)
check("signed_volume_translation_stable", abs(g["shells"][0]["signed_volume"] - 8) < 1e-6)

canonical = bpy.data.objects.new("canonical", positive)
bpy.context.scene.collection.objects.link(canonical)
hull = bpy.data.objects.new("hidden_hull", positive)
hidden = bpy.data.collections.new("Hidden hulls")
bpy.context.scene.collection.children.link(hidden)
hidden.objects.link(hull)
hidden.hide_viewport = True
hull.location = (4, 0, 0)
check("authored_hidden_transform_uses_location", abs(audit.authored_world_matrix(hull).translation.x - 4) < 1e-6)
check("point_probe_accounts_for_hidden_hull_translation", audit.hull_contains_local_point(hull, canonical, (4, 0, 0)))
check("opening_probe_outside_shifted_hull_is_clear", not audit.hull_contains_local_point(hull, canonical, (0, 0, 0)))

print("AUDIT_SELF_TESTS", json.dumps(results))
Path(__file__).with_name("validator_self_tests.json").write_text(json.dumps({"status": "PASS", "tests": results}, indent=2))
