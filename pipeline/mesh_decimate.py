"""Watertight, topology-preserving decimation to the submission budget (mesh pipeline v5, docs/mesh-v5-spec-draft.md
section 5; port of the v5 study's obsnew/scripts/decim.py, 2026-10-22). Mesh only: no scan, no mocap.

decimate(full) -> (mesh, info):
  - a mesh already within 4096 faces and 4096 vertices is returned as is;
  - otherwise open3d quadric decimation to 4096 faces (degenerate faces dropped, vertices welded);
  - if that changes the topology (watertight, body count, Euler number) or misses the budget: pymeshlab's
    topology-preserving quadric edge collapse in halving stages, then the target, retried up to 6 times at 0.9x;
  - if that fails too: GateFail('T'), and the candidate is not submitted.
The kit's budget_mesh must then leave the result unchanged apart from its zero-area padding (checked when the kit is
importable, --kit or V2D_KIT).

Why: the kit's own budget_mesh leaves only 6 of 144 full-resolution S1 meshes watertight [M, 2026-10-22]. Measured on
15 full-resolution meshes: open3d 15/15 watertight with topology kept, median 24 self-intersecting faces, p95 surface
deviation 0.49 mm; pymeshlab 15/15, median 8, p95 0.61 mm [M].
Collision pieces are built from the full-resolution mesh, never from this output (ep24: CoACD refilled the slot of the
4096-face file, 13.5 cm3 overlap against 6.7) [M].

Usage: python mesh_decimate.py FULL.glb OUT.glb [--report OUT.json] [--kit KITDIR]
Dependencies (the measured versions): open3d==0.20.0, pymeshlab==2025.7.post1, system package libopengl0.
"""
import argparse, contextlib, io, json, os, sys

import numpy as np
import trimesh

BUDGET = 4096


class GateFail(Exception):
    """A decimation gate failed; the letter names it (T = topology)."""


def merged(v, f):
    """Mesh from arrays with degenerate faces dropped and duplicate vertices welded."""
    f = np.asarray(f)
    f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])]
    return trimesh.Trimesh(np.asarray(v, float), f, process=True)


def topo(m):
    return dict(faces=int(len(m.faces)), verts=int(len(m.vertices)), watertight=bool(m.is_watertight),
                bodies=int(m.body_count), euler=int(m.euler_number))


def same_topology(a, b):
    return a['watertight'] and b['watertight'] and a['bodies'] == b['bodies'] and a['euler'] == b['euler']


def within(t, budget=BUDGET):
    return t['faces'] <= budget and t['verts'] <= budget


def by_open3d(m, budget=BUDGET):
    import open3d as o3d
    om = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(np.asarray(m.vertices, float)),
                                   o3d.utility.Vector3iVector(np.asarray(m.faces, np.int32)))
    r = om.simplify_quadric_decimation(target_number_of_triangles=budget)
    return merged(np.asarray(r.vertices), np.asarray(r.triangles))


def by_pymeshlab(m, budget=BUDGET, quality=0.3):
    import pymeshlab
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(np.asarray(m.vertices, float), np.asarray(m.faces, np.int32)))

    def qec(target):
        with contextlib.redirect_stdout(io.StringIO()):
            ms.meshing_decimation_quadric_edge_collapse(targetfacenum=int(target), preservetopology=True,
                                                        preserveboundary=True, preservenormal=True,
                                                        optimalplacement=True, planarquadric=True, qualitythr=quality,
                                                        autoclean=True)
    n = len(m.faces)
    while n > 2 * budget:                                # halving stages first (the study's staged variant)
        n = max(budget, n // 2); qec(n)
    target = budget
    for _ in range(6):                                   # topology preservation can stop above the target
        qec(target)
        cm = ms.current_mesh()
        if cm.face_number() <= budget and cm.vertex_number() <= budget:
            break
        target = int(target * 0.9)
    cm = ms.current_mesh()
    return merged(cm.vertex_matrix(), cm.face_matrix())


def decimate(full, budget=BUDGET):
    """(mesh, info). Raises GateFail('T') when neither method keeps the topology within the budget."""
    t0 = topo(full); info = dict(full=t0)
    if within(t0, budget):
        info['method'] = 'unchanged'; return full, info
    tries = []
    for name, fn in (('open3d', by_open3d), ('pymeshlab', by_pymeshlab)):
        try:
            m = fn(full, budget)
        except Exception as e:                           # a missing library or a library error: try the next one
            tries.append(dict(method=name, error=repr(e)[:200])); continue
        t = topo(m); tries.append(dict(method=name, **t))
        if within(t, budget) and same_topology(t0, t):
            info.update(method=name, out=t, tries=tries); return m, info
    info['tries'] = tries
    raise GateFail(f"T: no method kept the topology within {budget} faces / vertices: {json.dumps(info)[:600]}")


def kit_passthrough(path, kit=None, budget=BUDGET):
    """True when the kit's budget_mesh leaves the file unchanged apart from its zero-area padding; None without kit."""
    kit = kit or os.environ.get('V2D_KIT')
    if not kit:
        return None
    sys.path.insert(0, kit)
    from v2dlb.mesh_budget import budget_mesh
    v, f = budget_mesh(path, budget, budget)
    real = (f[:, 0] != f[:, 1]) | (f[:, 1] != f[:, 2])
    m = trimesh.load(path, force='mesh', process=True)
    return bool(real.sum() == len(m.faces) and len(np.unique(f[real])) == len(m.vertices))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('full'); ap.add_argument('out')
    ap.add_argument('--report'); ap.add_argument('--kit')
    a = ap.parse_args()
    full = trimesh.load(a.full, force='mesh', process=True)
    try:
        m, info = decimate(full)
    except GateFail as e:
        print('GATE FAIL', e); sys.exit(2)
    m.export(a.out)
    info['kit_passthrough'] = kit_passthrough(a.out, a.kit)
    if info['kit_passthrough'] is False:
        print('GATE FAIL T: the kit budget_mesh would change the decimated mesh', json.dumps(info)); sys.exit(2)
    print(json.dumps(info))
    if a.report:
        json.dump(info, open(a.report, 'w'), indent=1)


if __name__ == '__main__':
    main()
