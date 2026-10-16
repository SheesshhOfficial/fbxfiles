"""Read-only source QA. Run in Blender; writes only a separate JSON report.

blender -b INPUT.blend --python audit_blender_slice.py -- \
  --manifest MANIFEST.json --output /separate/audit.json

The schema adapter is deliberately isolated below. No Unreal result is inferred.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import bpy
from mathutils import Vector


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def native(value):
    if hasattr(value, "to_dict"):
        return {k: native(v) for k, v in value.to_dict().items()}
    if hasattr(value, "to_list"):
        return value.to_list()
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return str(value)


def props(obj):
    return {k: native(v) for k, v in obj.items() if k != "_RNA_UI"}


def authored_world_matrix(obj):
    """Hidden collections can have stale matrix_world caches after source save.

    This scene has ordinary static object parenting. Constraints/bone parenting
    are detected separately and are not silently approximated.
    """
    if obj.parent:
        return authored_world_matrix(obj.parent) @ obj.matrix_parent_inverse @ obj.matrix_basis
    return obj.matrix_basis.copy()


def truth(value):
    return value is True or value == 1 or str(value).lower() in {"true", "yes", "eligible", "prop"}


def first(d, keys, default=None):
    for key in keys:
        if key in d:
            return d[key]
    return default


def as_records(value, id_name):
    if isinstance(value, dict):
        return [dict(v, **{id_name: v.get(id_name, k)}) for k, v in value.items()]
    return value if isinstance(value, list) else []


def adapt_manifest(doc):
    """Return normalized records, preserving originals for narrowly scoped adapters."""
    assets = []
    for a in as_records(doc.get("assets", []), "asset_id"):
        aid = first(a, ("asset_id", "canonical_asset", "mesh_asset", "name"))
        col = a.get("collision", {})
        if not isinstance(col, dict):
            col = {}
        assets.append({
            "id": aid,
            "object": first(a, ("canonical_object", "source_object", "render_object", "blender_object", "mesh"), aid),
            "eligible": truth(first(a, ("eligible", "is_eligible", "prop_eligible"), False)),
            "materials": first(a, ("material_slots", "materials"), []),
            "hulls": first(a, ("collision_hulls", "hulls", "collision_objects"), col.get("hulls", [])),
            "pivot": first(a, ("pivot", "default_pivot")),
            "opening_probes": a.get("opening_probes", []),
            "raw": a,
        })
    placements = []
    asset_eligibility = {a["id"]: a["eligible"] for a in assets}
    records = as_records(doc.get("placements", []), "placement_id")
    if not records:
        records = as_records(doc.get("eligible_placements", []), "placement_id") + as_records(doc.get("fixture_placements", []), "placement_id") + as_records(doc.get("context_placements", []), "placement_id")
    for p in records:
        aid = first(p, ("asset_id", "mesh_asset", "canonical_asset", "asset"))
        placements.append({
            "id": first(p, ("placement_id", "id", "stable_id")),
            "object": first(p, ("blender_object", "object_name", "source_object", "object", "name")),
            "asset": aid,
            "eligible": truth(first(p, ("eligible", "is_eligible", "prop_eligible"), asset_eligibility.get(aid, False))),
            "class": first(p, ("actor_class", "unreal_actor_class", "export_actor_class", "intended_unreal_actor_class")),
            "tags": first(p, ("actor_tags", "tags", "unreal_tags"), []),
            "raw": p,
        })
    return assets, placements


def mesh_geometry(mesh, convex=False):
    """Check each edge-connected face shell without modifying source geometry."""
    mesh.calc_loop_triangles()
    verts = [v.co.copy() for v in mesh.vertices]
    finite = all(all(math.isfinite(x) for x in v) for v in verts)
    if not verts:
        return {"finite": finite, "vertices": 0, "polygons": len(mesh.polygons), "shells": []}
    minimum = [min(v[i] for v in verts) for i in range(3)]
    maximum = [max(v[i] for v in verts) for i in range(3)]
    diagonal = (Vector(maximum) - Vector(minimum)).length
    area_eps = max(diagonal * diagonal * 1e-12, 1e-16)
    volume_eps = max(diagonal ** 3 * 1e-12, 1e-18)
    edge_faces = defaultdict(list)
    for poly in mesh.polygons:
        vs = list(poly.vertices)
        for a, b in zip(vs, vs[1:] + vs[:1]):
            edge_faces[tuple(sorted((a, b)))].append((poly.index, a < b))
    adj = defaultdict(set)
    for uses in edge_faces.values():
        for i, _ in uses:
            adj[i].update(j for j, _ in uses if j != i)
    component_of = {}
    shells = []
    for poly in mesh.polygons:
        if poly.index in component_of:
            continue
        cid = len(shells)
        stack = [poly.index]
        fs = []
        component_of[poly.index] = cid
        while stack:
            i = stack.pop()
            fs.append(i)
            for j in adj[i]:
                if j not in component_of:
                    component_of[j] = cid
                    stack.append(j)
        indices = sorted({j for i in fs for j in mesh.polygons[i].vertices})
        center = sum((verts[j] for j in indices), Vector()) / len(indices)
        face_set = set(fs)
        edges = [uses for uses in edge_faces.values() if uses[0][0] in face_set]
        boundary = sum(len(uses) == 1 for uses in edges)
        nonmanifold = sum(len(uses) > 2 for uses in edges)
        inconsistent = sum(len(uses) == 2 and uses[0][1] == uses[1][1] for uses in edges)
        shells.append({
            "index": cid, "polygon_count": len(fs), "vertex_count": len(indices),
            "boundary_edges": boundary, "nonmanifold_edges": nonmanifold,
            "inconsistently_wound_edges": inconsistent,
            "closed": boundary == 0 and nonmanifold == 0,
            "material_slots": sorted({mesh.polygons[i].material_index for i in fs}),
            "material_names": sorted({mesh.materials[mesh.polygons[i].material_index].name
                if mesh.polygons[i].material_index < len(mesh.materials) and mesh.materials[mesh.polygons[i].material_index] else "<missing>" for i in fs}),
            "signed_volume": 0.0, "degenerate_triangles": 0,
            "bounds_min": [min(verts[j][i] for j in indices) for i in range(3)],
            "bounds_max": [max(verts[j][i] for j in indices) for i in range(3)],
            "_center": center,
        })
    for tri in mesh.loop_triangles:
        shell = shells[component_of[tri.polygon_index]]
        a, b, c = (verts[i] - shell["_center"] for i in tri.vertices)
        area = (b - a).cross(c - a).length / 2
        shell["degenerate_triangles"] += int(area <= area_eps)
        shell["signed_volume"] += a.dot(b.cross(c)) / 6
    for shell in shells:
        del shell["_center"]
        volume = shell["signed_volume"]
        shell["orientation"] = "positive" if volume > volume_eps else "negative" if volume < -volume_eps else "zero"
        # Bounding containment is a diagnostic hint, not proof of an intentional cavity.
        shell["bounding_containers"] = [other["index"] for other in shells if other is not shell and
            all(other["bounds_min"][i] <= shell["bounds_min"][i] + diagonal * 1e-6 and
                other["bounds_max"][i] >= shell["bounds_max"][i] - diagonal * 1e-6 for i in range(3)) and
            abs(other["signed_volume"]) > abs(volume) + volume_eps]
    convex_violations = []
    if convex:
        tolerance = max(diagonal * 1e-6, 1e-8)
        for poly in mesh.polygons:
            if not poly.vertices:
                continue
            point = verts[poly.vertices[0]]
            outside = max(poly.normal.dot(v - point) for v in verts)
            if outside > tolerance:
                convex_violations.append({"polygon": poly.index, "max_outside": outside})
    h = hashlib.sha256()
    h.update(json.dumps([[round(c, 9) for c in v] for v in verts]).encode())
    h.update(json.dumps([(list(p.vertices), p.material_index) for p in mesh.polygons]).encode())
    h.update(json.dumps([m.name if m else None for m in mesh.materials]).encode())
    return {
        "finite": finite, "vertices": len(verts), "polygons": len(mesh.polygons),
        "triangles": len(mesh.loop_triangles), "bounds_min": minimum, "bounds_max": maximum,
        "dimensions": [maximum[i] - minimum[i] for i in range(3)],
        "shells": shells, "convex_violation_count": len(convex_violations),
        "convex_violation_samples": convex_violations[:10],
        "material_slots": [m.name if m else None for m in mesh.materials],
        "invalid_material_indices": sum(p.material_index >= len(mesh.materials) for p in mesh.polygons) if mesh.materials else len(mesh.polygons),
        "uv_layers": [layer.name for layer in mesh.uv_layers], "geometry_material_sha256": h.hexdigest(),
    }


def hull_contains_local_point(hull, canonical, point, tolerance=1e-6):
    """Convex halfspace containment, with probe expressed in canonical mesh space."""
    local = authored_world_matrix(hull).inverted() @ (authored_world_matrix(canonical) @ Vector(point))
    return all(p.normal.dot(local - hull.data.vertices[p.vertices[0]].co) <= tolerance for p in hull.data.polygons)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--probe-spec", help="Independent canonical-local empty-space probes")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source = Path(bpy.data.filepath).resolve()
    manifest_path = Path(args.manifest).resolve()
    output = Path(args.output).resolve()
    if output == source or output == manifest_path:
        raise RuntimeError("QA output cannot overwrite an input")
    initial_hash = sha256_file(source)
    doc = json.loads(manifest_path.read_text())
    assets, placements = adapt_manifest(doc)
    independent_probes = json.loads(Path(args.probe_spec).read_text()) if args.probe_spec else {}
    for asset in assets:
        asset["opening_probes"] += independent_probes.get(asset["id"], [])
    report = {
        "schema": "evergreen-premium-independent-source-audit-v1",
        "blender_version": bpy.app.version_string,
        "source": str(source), "source_sha256": initial_hash,
        "manifest": str(manifest_path), "manifest_sha256": sha256_file(manifest_path),
        "scope": "Read-only Blender geometry and manifest audit. No Unreal execution.",
        "unreal_import_tested": False, "character_collision_tested": False,
        "interaction_tested": False, "multiplayer_tested": False,
        "fbx_round_trip_tested": False, "id_stability_across_rebuilds_tested": False,
        "limitations": [
            "Source audit covers canonical assets, placements and classified context; it is not an Unreal export acceptance.",
            "Nonblocking visual details are explicit source exceptions and must retain those categories during import.",
            "Empty-region point probes do not prove swept player/disguise clearance.",
            "Hidden collision-object cached world matrices may be stale; audit uses authored static transforms.",
        ],
        "errors": [], "warnings": [], "meshes": {}, "evaluated_meshes": {}, "objects": {}, "assets": {}, "placements": [],
    }
    def error(code, target, detail):
        report["errors"].append({"code": code, "target": target, "detail": detail})
    def warning(code, target, detail):
        report["warnings"].append({"code": code, "target": target, "detail": detail})

    if not assets:
        error("NO_ASSET_RECORDS", "manifest", "Canonical asset inventory absent or schema unrecognized")
    if not placements:
        error("NO_PLACEMENT_RECORDS", "manifest", "Per-placement inventory absent or schema unrecognized")
    mesh_objects = [o for o in bpy.data.objects if o.type == "MESH"]
    declared_open_meshes = {}
    for asset in assets:
        obj = bpy.data.objects.get(asset["object"] or "")
        note = asset["raw"].get("render_open_surfaces")
        if obj and obj.type == "MESH" and note:
            declared_open_meshes[obj.data.name] = note
    for obj in mesh_objects:
        is_hull = obj.name.startswith(("UCX_", "UBX_", "UCP_", "USP_"))
        key = obj.data.name + ("::collision" if is_hull else "::render")
        if key not in report["meshes"]:
            geo = mesh_geometry(obj.data, convex=is_hull)
            geo["objects"] = []
            report["meshes"][key] = geo
            if not geo["finite"]:
                error("NONFINITE_GEOMETRY", key, "Non-finite vertex coordinates")
            for shell in geo["shells"]:
                target = f"{key}/shell_{shell['index']}"
                if shell["degenerate_triangles"]:
                    error("DEGENERATE_TRIANGLES", target, shell["degenerate_triangles"])
                if shell["inconsistently_wound_edges"]:
                    error("INCONSISTENT_WINDING", target, shell["inconsistently_wound_edges"])
                if is_hull and not shell["closed"]:
                    error("OPEN_COLLISION_SHELL", target, shell)
                elif not shell["closed"]:
                    if obj.data.name in declared_open_meshes and shell["material_names"] and all(name.startswith("Label ") for name in shell["material_names"]):
                        shell["intentional_open_classification"] = "Printed label surface, corroborated by material and asset declaration"
                        shell["declaration"] = declared_open_meshes[obj.data.name]
                    elif obj.data.name in declared_open_meshes and "lettering" in str(declared_open_meshes[obj.data.name]).lower() and shell["material_names"] == ["Paper ivory"] and shell["bounds_max"][0] - shell["bounds_min"][0] <= 0.001 and abs(shell["bounds_max"][0] - geo["bounds_max"][0]) <= 0.001:
                        shell["intentional_open_classification"] = "Converted side-lettering surface, thin at package side, corroborated by source declaration"
                        shell["declaration"] = declared_open_meshes[obj.data.name]
                    else:
                        warning("OPEN_RENDER_SHELL", target, "Requires intentional-surface classification; may be a valid label/decal")
                if shell["closed"] and shell["orientation"] != "positive":
                    if not is_hull and shell["orientation"] == "negative" and shell["bounding_containers"]:
                        warning("NEGATIVE_NESTED_RENDER_SHELL", target, "Possible intentional inner cavity; explicit classification and inspection required")
                    else:
                        error("NONPOSITIVE_CLOSED_SHELL", target, shell["signed_volume"])
            if is_hull:
                if len(geo["shells"]) != 1:
                    error("MULTIPLE_SHELLS_IN_HULL", key, len(geo["shells"]))
                if geo["convex_violation_count"]:
                    error("NONCONVEX_OR_INWARD_HULL", key, geo["convex_violation_samples"])
        report["meshes"][key]["objects"].append(obj.name)
        op = props(obj)
        report["objects"][obj.name] = {
            "mesh": key, "properties": op,
            "collections": [c.name for c in obj.users_collection],
            "location": list(obj.location), "rotation_euler": list(obj.rotation_euler), "scale": list(obj.scale),
            "world_matrix": [list(row) for row in authored_world_matrix(obj)],
            "cached_world_matrix": [list(row) for row in obj.matrix_world],
            "cached_world_matrix_stale": any(abs(a-b)>1e-6 for row_a,row_b in zip(obj.matrix_world, authored_world_matrix(obj)) for a,b in zip(row_a,row_b)),
            "material_slots": [{"name": s.material.name if s.material else None, "link": s.link} for s in obj.material_slots],
            "modifiers": [{"name": m.name, "type": m.type, "viewport": m.show_viewport, "render": m.show_render} for m in obj.modifiers],
        }
        if obj.modifiers:
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            evaluated_mesh = evaluated.to_mesh()
            eg = mesh_geometry(evaluated_mesh, convex=is_hull)
            report["evaluated_meshes"][obj.name] = eg
            evaluated.to_mesh_clear()
            if not eg["finite"] or any(s["degenerate_triangles"] or s["inconsistently_wound_edges"] or (s["closed"] and s["orientation"] != "positive") for s in eg["shells"]):
                error("EVALUATED_GEOMETRY_ERROR", obj.name, "Evaluated modifier geometry has degeneracy or winding issues")
            if any(m.show_viewport != m.show_render for m in obj.modifiers):
                warning("MODIFIER_RENDER_VIEWPORT_MISMATCH", obj.name, "Evaluated viewport result may differ from rendered/exported geometry")
        if obj.constraints or (obj.parent and obj.parent_type != "OBJECT"):
            warning("NONSTATIC_TRANSFORM_DEPENDENCY", obj.name, "Authored static transform calculation requires explicit constraint/parent evaluation")
        if is_hull and authored_world_matrix(obj).to_3x3().determinant() <= 0:
            error("NONPOSITIVE_HULL_TRANSFORM", obj.name, list(obj.scale))
        if is_hull and obj.get("canonical_hull_transform_baked") and any(abs(obj.matrix_basis[i][j] - (1 if i == j else 0)) > 1e-6 for i in range(4) for j in range(4)):
            error("DECLARED_BAKED_HULL_TRANSFORM_NOT_IDENTITY", obj.name, [list(row) for row in obj.matrix_basis])

    asset_ids = [a["id"] for a in assets]
    for aid, count in Counter(asset_ids).items():
        if aid is None or count != 1:
            error("DUPLICATE_OR_MISSING_ASSET_ID", str(aid), count)
    asset_map = {a["id"]: a for a in assets}
    eligible_assets = {p["asset"] for p in placements if p["eligible"]} | {a["id"] for a in assets if a["eligible"]}
    for asset in assets:
        aid = asset["id"]
        obj = bpy.data.objects.get(asset["object"] or "")
        if obj is None or obj.type != "MESH":
            error("CANONICAL_OBJECT_MISSING", str(aid), asset["object"])
            continue
        geo = report["meshes"][report["objects"][obj.name]["mesh"]]
        hulls = asset["hulls"] or [o.name for o in mesh_objects if re.fullmatch(r"UCX_" + re.escape(obj.name) + r"_\d+", o.name)]
        hulls = [h if isinstance(h, str) else first(h, ("object", "name", "object_name")) for h in hulls]
        report["assets"][aid] = {"canonical_object": obj.name, "hulls": hulls, "eligible": aid in eligible_assets}
        if not hulls:
            error("PHYSICAL_CANONICAL_ASSET_NO_COLLISION", str(aid), obj.name)
        declared_hull_count = asset["raw"].get("collision_hull_count")
        if declared_hull_count is not None and declared_hull_count != len(hulls):
            error("COLLISION_HULL_COUNT_MISMATCH", str(aid), {"declared": declared_hull_count, "actual": len(hulls)})
        dimensions = asset["raw"].get("dimensions_m")
        if dimensions and any(abs(float(a) - float(b)) > 1e-5 for a,b in zip(dimensions, geo["dimensions"])):
            error("ASSET_DIMENSIONS_MISMATCH", str(aid), {"declared": dimensions, "actual": geo["dimensions"]})
        for name in hulls:
            hull = bpy.data.objects.get(name or "")
            if hull is None:
                error("HULL_OBJECT_MISSING", str(aid), name)
            elif not re.fullmatch(r"(?:UCX|UBX|UCP|USP)_" + re.escape(obj.name) + r"(?:_\d+)?", hull.name):
                error("HULL_RENDER_NAME_MISMATCH", str(aid), name)
            elif hull.type == "MESH":
                local_matrix = authored_world_matrix(obj).inverted() @ authored_world_matrix(hull)
                points = [local_matrix @ v.co for v in hull.data.vertices]
                tolerance = max(max(geo["dimensions"]) * 0.02, 0.005)
                if points and any(min(p[i] for p in points) < geo["bounds_min"][i] - tolerance or
                                  max(p[i] for p in points) > geo["bounds_max"][i] + tolerance for i in range(3)):
                    warning("COLLISION_EXTENDS_BEYOND_RENDER", str(aid), {"hull": hull.name, "tolerance": tolerance})
        probe_results = []
        for index, probe in enumerate(asset["opening_probes"]):
            point = probe.get("point") if isinstance(probe, dict) else probe
            if not isinstance(point, (list, tuple)) or len(point) != 3:
                error("INVALID_OPENING_PROBE", str(aid), probe)
                continue
            blockers = [name for name in hulls if bpy.data.objects.get(name or "") is not None and
                        hull_contains_local_point(bpy.data.objects[name], obj, point)]
            probe_results.append({"probe": probe, "blocked_by": blockers})
            if blockers:
                error("REQUIRED_OPENING_BLOCKED", str(aid), {"probe": probe, "blockers": blockers})
        report["assets"][aid]["opening_probe_results"] = probe_results
        if aid in eligible_assets:
            if not hulls:
                error("ELIGIBLE_ASSET_NO_COLLISION", str(aid), obj.name)
            if any(abs(v - 1) > 1e-6 for v in obj.scale):
                error("CANONICAL_NONUNIT_SCALE", str(aid), list(obj.scale))
            if asset["pivot"] is None:
                error("PIVOT_UNDECLARED", str(aid), "Expected deliberate canonical pivot metadata")
            elif "bottom" in str(asset["pivot"]).lower() and "cent" in str(asset["pivot"]).lower():
                lo, hi = geo["bounds_min"], geo["bounds_max"]
                # Small rims/printed details need not define the authored primary-body pivot.
                tol = max(max(geo["dimensions"]) * 0.005, 0.002)
                report["assets"][aid]["pivot_tolerance_m"] = tol
                if abs(lo[2]) > tol or abs((lo[0] + hi[0]) / 2) > tol or abs((lo[1] + hi[1]) / 2) > tol:
                    error("BOTTOM_CENTER_PIVOT_MISMATCH", str(aid), {"min": lo, "max": hi})
            if any(s.link != "DATA" for s in obj.material_slots):
                error("CANONICAL_OBJECT_MATERIAL_OVERRIDE", str(aid), "Materials must be stored on the asset")
            if asset["materials"] and geo["material_slots"] != asset["materials"]:
                error("MATERIAL_SLOT_MANIFEST_MISMATCH", str(aid), {"source": geo["material_slots"], "manifest": asset["materials"]})
            if geo["invalid_material_indices"]:
                error("INVALID_RENDER_MATERIAL_INDICES", str(aid), geo["invalid_material_indices"])

    report["carton_side_lettering_checks"] = []
    for aid,w,d,h in [("rolled_oats",.151,.073,.267),("almond_granola",.145,.072,.250),("bronze_pasta",.113,.058,.304),("sea_salt",.088,.055,.150)]:
        asset = asset_map.get(aid)
        obj = bpy.data.objects.get(asset["object"] or "") if asset else None
        if obj is None:
            continue
        lettering = [v.co for v in obj.data.vertices if v.co.x > w/2+.0001]
        inside = bool(lettering) and all(abs(v.y) <= d/2+.001 and -.001 <= v.z <= h+.001 for v in lettering)
        report["carton_side_lettering_checks"].append({"asset": aid, "fits_side_panel": inside})
        if not inside:
            error("CARTON_SIDE_LETTERING_OUTSIDE_PANEL", aid, "Side typography must fit within the physical carton side")

    placement_ids = [p["id"] for p in placements]
    for pid, count in Counter(placement_ids).items():
        if pid is None or count != 1:
            error("DUPLICATE_OR_MISSING_PLACEMENT_ID", str(pid), count)
    objects_seen = Counter(p["object"] for p in placements)
    for obj_name, count in objects_seen.items():
        if obj_name is None or count != 1:
            error("DUPLICATE_OR_MISSING_PLACEMENT_OBJECT", str(obj_name), count)
    for p in placements:
        obj = bpy.data.objects.get(p["object"] or "")
        report["placements"].append({k: v for k, v in p.items() if k != "raw"})
        if p["asset"] not in asset_map:
            error("PLACEMENT_ASSET_MISSING", str(p["id"]), p["asset"])
        if obj is None:
            error("PLACEMENT_OBJECT_MISSING", str(p["id"]), p["object"])
            continue
        op = props(obj)
        actual_id = first(op, ("stable_id", "placement_id", "id"))
        if actual_id != p["id"]:
            error("PLACEMENT_SOURCE_ID_MISMATCH", str(p["id"]), actual_id)
        if op.get("asset_id") != p["asset"]:
            error("PLACEMENT_SOURCE_ASSET_ID_MISMATCH", str(p["id"]), op.get("asset_id"))
        world = authored_world_matrix(obj)
        expected_position = p["raw"].get("position_m")
        if expected_position and any(abs(float(a)-float(b))>1e-5 for a,b in zip(expected_position, world.translation)):
            error("PLACEMENT_POSITION_MISMATCH", str(p["id"]), {"source": list(world.translation), "manifest": expected_position})
        expected_rotation = p["raw"].get("rotation_euler_deg")
        if expected_rotation:
            angles = [math.degrees(v) for v in obj.rotation_euler]
            if any(abs((a-b+180)%360-180)>1e-4 for a,b in zip(expected_rotation,angles)):
                error("PLACEMENT_ROTATION_MISMATCH", str(p["id"]), {"source": angles, "manifest": expected_rotation})
        if not p["eligible"]:
            asset = asset_map.get(p["asset"])
            canonical = bpy.data.objects.get(asset["object"] or "") if asset else None
            if obj.type != "MESH" or canonical is None or canonical.type != "MESH":
                error("STATIC_PLACEMENT_CANONICAL_MESH_MISSING", str(p["id"]), p["asset"])
            elif obj.data != canonical.data:
                source_key = report["objects"][obj.name]["mesh"]
                canon_key = report["objects"][canonical.name]["mesh"]
                if report["meshes"][source_key]["geometry_material_sha256"] != report["meshes"][canon_key]["geometry_material_sha256"]:
                    error("STATIC_PLACEMENT_CANONICAL_MISMATCH", str(p["id"]), p["asset"])
            if p["class"] != "StaticMeshActor" or any(s.link != "DATA" for s in obj.material_slots):
                error("STATIC_PLACEMENT_EXPORT_CONTRACT_MISMATCH", str(p["id"]), "Expected individual StaticMeshActor with asset-level materials")
            continue
        if obj.type != "MESH" or obj.instance_type != "NONE":
            error("ELIGIBLE_INSTANCE_OR_NONMESH", str(p["id"]), {"type": obj.type, "instance_type": obj.instance_type})
        if any(abs(v - 1) > 1e-6 for v in obj.scale):
            error("ELIGIBLE_LOCAL_NONUNIT_SCALE", str(p["id"]), list(obj.scale))
        if any(abs(v - 1) > 1e-6 for v in authored_world_matrix(obj).to_scale()):
            error("ELIGIBLE_PLACEMENT_NONUNIT_SCALE", str(p["id"]), list(authored_world_matrix(obj).to_scale()))
        if p["class"] not in {"StaticMeshActor", "/Script/Engine.StaticMeshActor", "unreal.StaticMeshActor"}:
            error("ELIGIBLE_WRONG_ACTOR_CLASS", str(p["id"]), p["class"])
        tags = p["tags"] if isinstance(p["tags"], list) else [p["tags"]]
        if "Prop" not in tags:
            error("ELIGIBLE_PROP_TAG_MISSING", str(p["id"]), tags)
        if not truth(op.get("Prop")) or "Prop" not in str(op.get("tags", "")).split(","):
            error("ELIGIBLE_SOURCE_PROP_METADATA_MISSING", str(p["id"]), {"Prop": op.get("Prop"), "tags": op.get("tags")})
        if any(s.link != "DATA" for s in obj.material_slots):
            error("ELIGIBLE_INSTANCE_MATERIAL_OVERRIDE", str(p["id"]), obj.name)
        if any(m.type in {"NODES", "PARTICLE_SYSTEM", "ARRAY"} and (m.show_viewport or m.show_render) for m in obj.modifiers):
            error("ELIGIBLE_POTENTIAL_HIDDEN_INSTANCES", str(p["id"]), [m.type for m in obj.modifiers])
        asset = asset_map.get(p["asset"])
        canonical = bpy.data.objects.get(asset["object"] or "") if asset else None
        if canonical and obj.type == "MESH":
            if obj.data != canonical.data:
                canonical_key = report["objects"][canonical.name]["mesh"]
                actual_key = report["objects"][obj.name]["mesh"]
                if report["meshes"][canonical_key]["geometry_material_sha256"] != report["meshes"][actual_key]["geometry_material_sha256"]:
                    error("PLACEMENT_CANONICAL_GEOMETRY_MISMATCH", str(p["id"]), p["asset"])
                else:
                    warning("DUPLICATED_MESH_DATA", str(p["id"]), "Identical geometry but mesh data is not shared")

    # Source metadata supplies independent evidence of omitted or downgraded eligible copies.
    manifested = {p["object"]: p for p in placements}
    for obj in bpy.data.objects:
        op = props(obj)
        declared = truth(first(op, ("eligible", "is_eligible", "prop_eligible", "Prop"), False))
        role = str(first(op, ("role", "source_role", "object_role"), "")).lower()
        in_eligible_collection = any(c.name == "03_ELIGIBLE_PROP_PLACEMENTS" for c in obj.users_collection)
        if in_eligible_collection and obj.name not in manifested:
            error("ELIGIBLE_COLLECTION_OBJECT_OMITTED", obj.name, "Every eligible collection object needs a placement record")
        elif in_eligible_collection and not manifested[obj.name]["eligible"]:
            error("ELIGIBLE_COLLECTION_OBJECT_DOWNGRADED", obj.name, manifested[obj.name]["id"])
        if declared and role not in {"canonical", "asset", "prototype", "collision"}:
            if obj.name not in manifested:
                warning("SOURCE_ELIGIBLE_OBJECT_NOT_IN_PLACEMENTS", obj.name, "Determine whether canonical prototype or an omitted eligible placement")
            elif not manifested[obj.name]["eligible"]:
                error("ELIGIBILITY_DOWNGRADED_IN_MANIFEST", obj.name, manifested[obj.name]["id"])
    missing_images = []
    for image in bpy.data.images:
        if image.source == "FILE" and not image.packed_file and image.filepath:
            path = Path(bpy.path.abspath(image.filepath))
            if not path.is_file():
                missing_images.append({"image": image.name, "path": str(path)})
    for record in missing_images:
        error("MISSING_EXTERNAL_IMAGE", record["image"], record["path"])
    inventory = doc.get("scene_context_inventory", [])
    context_by_name = {}
    report["context_inventory"] = inventory
    for record in inventory:
        name = record.get("object_name")
        if name in context_by_name:
            error("DUPLICATE_CONTEXT_INVENTORY_OBJECT", str(name), "Context object appears more than once")
        context_by_name[name] = record
        obj = bpy.data.objects.get(name or "")
        if obj is None:
            error("CONTEXT_OBJECT_MISSING", str(name), record.get("stable_id"))
            continue
        if obj.get("stable_id") != record.get("stable_id"):
            error("CONTEXT_ID_MISMATCH", str(name), {"source": obj.get("stable_id"), "manifest": record.get("stable_id")})
        if truth(record.get("eligible")) or truth(obj.get("Prop")):
            error("CONTEXT_UNEXPECTED_ELIGIBILITY", str(name), "Eligible objects must occur in eligible placement inventory")
        if record.get("collision_status") == "INTENTIONAL_NONBLOCKING":
            if not record.get("category") or not record.get("justification"):
                error("NONBLOCKING_CONTEXT_UNJUSTIFIED", str(name), record)
            if obj.get("collision_category") != record["category"] or not obj.get("nonblocking_reason"):
                error("NONBLOCKING_SOURCE_METADATA_MISSING", str(name), record["category"])
        elif record.get("category") in {"structural_static", "fixture_static"}:
            if name not in manifested or not record.get("collision_objects") or record.get("asset_id") not in asset_map:
                error("PHYSICAL_CONTEXT_COLLISION_INCOMPLETE", str(name), record)
        else:
            error("CONTEXT_COLLISION_UNCLASSIFIED", str(name), record)
    id_to_objects = defaultdict(set)
    for p in placements:
        id_to_objects[p["id"]].add(p["object"])
    for record in inventory:
        id_to_objects[record.get("stable_id")].add(record.get("object_name"))
    for ident,names in id_to_objects.items():
        if ident is None or len(names) != 1:
            error("GLOBAL_PLACEMENT_ID_COLLISION", str(ident), sorted(names))
    covered_objects = set(p["object"] for p in placements) | set(a["object"] for a in assets) | set(h for a in report["assets"].values() for h in a["hulls"]) | set(context_by_name)
    report["unmanifested_mesh_objects"] = [o.name for o in mesh_objects if o.name not in covered_objects]
    report["unclassified_render_objects"] = [o.name for o in bpy.data.objects if o.type in {"MESH", "FONT", "CURVE", "SURFACE"} and o.name not in covered_objects]
    for name in report["unclassified_render_objects"]:
        error("UNCLASSIFIED_SCENE_RENDER_OBJECT", name, "Every scene geometry object must be a canonical asset, placement, hull or explicit context classification")
    report["packed_file_images"] = [i.name for i in bpy.data.images if i.source == "FILE" and i.packed_file]
    report["foundation_source_probes"] = []
    floor_place = next((p for p in placements if p["asset"] == "context_floor_slab"), None)
    if floor_place:
        placed = bpy.data.objects[floor_place["object"]]
        canonical = bpy.data.objects[asset_map["context_floor_slab"]["object"]]
        for x in [-1,0,1]:
            for y in [0,2.5,5]:
                point = Vector((x,y,-.04))
                canonical_point = authored_world_matrix(placed).inverted() @ point
                containing = [name for name in report["assets"]["context_floor_slab"]["hulls"] if hull_contains_local_point(bpy.data.objects[name], canonical, canonical_point)]
                report["foundation_source_probes"].append({"world_point_m": list(point), "contained_by": containing})
                if not containing:
                    error("FOUNDATION_SOURCE_PROBE_MISSES_HULL", str(list(point)), "Expected continuous authored floor slab below aisle")
    else:
        error("FOUNDATION_SOURCE_ASSET_MISSING", "context_floor_slab", "Physical floor coverage is required for this source slice")
    invariants = {
        "meshes": {k: g["geometry_material_sha256"] for k,g in report["meshes"].items()},
        "placements": [{"id": p["id"], "asset": p["asset"], "eligible": p["eligible"], "world_matrix": report["objects"][p["object"]]["world_matrix"]} for p in placements],
        "asset_hulls": {k: a["hulls"] for k,a in report["assets"].items()},
    }
    report["geometry_placement_fingerprint_sha256"] = hashlib.sha256(json.dumps(invariants, sort_keys=True).encode()).hexdigest()
    report["summary"] = {
        "scene_objects": len(bpy.data.objects), "mesh_objects": len(mesh_objects),
        "unique_mesh_datablocks": len({o.data.as_pointer() for o in mesh_objects}),
        "manifest_assets": len(assets), "eligible_assets": len(eligible_assets),
        "manifest_placements": len(placements), "eligible_placements": sum(p["eligible"] for p in placements),
        "collision_objects": sum(o.name.startswith(("UCX_", "UBX_", "UCP_", "USP_")) for o in mesh_objects),
        "render_closed_shells": sum(s["closed"] for k, g in report["meshes"].items() if k.endswith("::render") for s in g["shells"]),
        "render_negative_closed_shells": sum(s["closed"] and s["orientation"] == "negative" for k, g in report["meshes"].items() if k.endswith("::render") for s in g["shells"]),
        "classified_open_render_shells": sum(bool(s.get("intentional_open_classification")) for k,g in report["meshes"].items() if k.endswith("::render") for s in g["shells"]),
        "evaluated_modifier_meshes": len(report["evaluated_meshes"]),
        "unmanifested_mesh_objects": len(report["unmanifested_mesh_objects"]),
        "unclassified_render_objects": len(report["unclassified_render_objects"]),
        "context_inventory_records": len(inventory),
        "physical_context_placements": len(doc.get("context_placements", [])),
        "intentional_nonblocking_context_objects": sum(r.get("collision_status") == "INTENTIONAL_NONBLOCKING" for r in inventory),
        "cached_world_matrix_stale_objects": sum(o["cached_world_matrix_stale"] for o in report["objects"].values()),
        "opening_probes": sum(len(a["opening_probe_results"]) for a in report["assets"].values()),
        "blocked_opening_probes": sum(bool(p["blocked_by"]) for a in report["assets"].values() for p in a["opening_probe_results"]),
        "packed_file_images": len(report["packed_file_images"]),
        "foundation_source_probes": len(report["foundation_source_probes"]),
        "errors": len(report["errors"]), "warnings": len(report["warnings"]),
    }
    report["source_unchanged"] = sha256_file(source) == initial_hash
    if not report["source_unchanged"]:
        error("SOURCE_CHANGED_DURING_AUDIT", str(source), "Concurrent build or unexpected write; rerun against a stable file")
    report["status"] = "FAIL" if report["errors"] else "REVIEW_REQUIRED" if report["warnings"] else "PASS_SOURCE_ONLY"
    report["summary"]["errors"] = len(report["errors"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    print("INDEPENDENT_AUDIT", report["status"], json.dumps(report["summary"]))
    print("INDEPENDENT_AUDIT_REPORT", str(output))


if __name__ == "__main__":
    main()
