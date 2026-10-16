"""Conservative closed, consistently oriented, negative-volume shell classifier."""
import collections, math
from mathutils import Vector

def analyze(me):
    """Connected vertex shells with both topological and oriented-manifold tests."""
    me.calc_loop_triangles()
    parents = list(range(len(me.vertices)))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for e in me.edges:
        a, b = map(find, e.vertices)
        parents[a] = b
    groups = collections.defaultdict(list)
    for p in me.polygons:
        groups[find(p.vertices[0])].append(p.index)
    tri_groups = collections.defaultdict(list)
    for t in me.loop_triangles:
        tri_groups[find(t.vertices[0])].append(t)
    results = []
    for root, pids in groups.items():
        vids = sorted({v for pi in pids for v in me.polygons[pi].vertices})
        points = [me.vertices[v].co for v in vids]
        lo = [min((v[j] for v in points)) for j in range(3)]
        hi = [max((v[j] for v in points)) for j in range(3)]
        origin = Vector(tuple(((a + b) / 2 for a, b in zip(lo, hi))))
        threshold = max(1e-15, (Vector(hi) - Vector(lo)).length ** 3 * 1e-12)
        edges = collections.defaultdict(list)
        for pi in pids:
            vs = list(me.polygons[pi].vertices)
            for a, b in zip(vs, vs[1:] + vs[:1]):
                edges[tuple(sorted((a, b)))].append(1 if a < b else -1)
        closed = bool(edges) and all((len(ds) == 2 for ds in edges.values()))
        oriented = closed and all((sum(ds) == 0 for ds in edges.values()))
        volume = math.fsum(((me.vertices[t.vertices[0]].co - origin).dot((me.vertices[t.vertices[1]].co - origin).cross(me.vertices[t.vertices[2]].co - origin)) / 6 for t in tri_groups[root]))
        eligible = closed and oriented and (volume < -threshold)
        results.append(dict(shell_index=len(results), vertices=len(vids), polygons=len(pids), triangles=len(tri_groups[root]), closed=closed, consistently_oriented=oriented, signed_volume_m3=volume, volume_threshold_m3=threshold, eligible_for_flip=eligible, polygon_indices=pids))
    return results
