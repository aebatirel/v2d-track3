"""GT-free mesh gates of the v5 selection (docs/mesh-v5-spec-draft.md section 4.5 and 6; port of the v5 study's
metric/xreg.py, spoon/code/xcheck.py, spec/e0c_consistency.py and the needed mesh_metric.py helpers, 2026-10-22).
Every gate compares two of OUR meshes in the same body frame with the kit's own scorer functions (AUC.py
_register_object_body, CD-O.py _object_chamfer_cm); no scan, no mocap.

  flip_check(cand, ref, name)  X: the candidate registered to our reference mesh (M0 of the same build; per episode also
                               the tracking seed, owner decision O3) at every eval seed of the object plus extra seeds up
                               to 6; fails on a rotation > 90 deg (declared symmetries excluded)
  consistency(cand, seed)      C (per episode only): kit CD-O chamfer, Sim(3), mean over seeds 11 and 22; <= 0.5 cm [H]
  registration_move(cand, ref) G6 (support rule): registering the flattened mesh to the unflattened one moves it <= 2 mm
                               and <= 2 deg at every seed
  topology(mesh)               T: every body watertight, <= 4096 faces and vertices (body count and Euler number are
                               compared before / after decimation by pipeline/mesh_decimate.py)
Meshes are decoded as the scorer decodes them: the kit packer's budget_mesh (weld, simplify, pad).
Usage: python mesh_gates.py {flip|consistency|g6} CAND.glb REF.glb [OBJECT] [--kit KIT]
"""
import argparse, importlib.util, json, math, os, sys

import numpy as np

EXTRA_SEEDS = (11, 22, 33, 44, 55, 66)
BUDGET = 4096
_K = {}


def kit(path=None):
    """The kit's AUC and CD-O scorer modules, budget_mesh and sample_vertices (V2D_KIT or /content/kit/...)."""
    if 'auc' in _K:
        return _K
    path = path or os.environ.get('V2D_KIT', '/content/kit/v2d_submission_kit')

    def load(name, rel):
        spec = importlib.util.spec_from_file_location(name, f'{path}/{rel}')
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
    _K['auc'] = load('kit_auc', 'metric_code/track_3/AUC.py'); _K['cdo'] = load('kit_cdo', 'metric_code/track_3/CD-O.py')
    sys.path.insert(0, path)
    from v2dlb.mesh_budget import budget_mesh
    from v2dlb.vertices import sample_vertices
    _K.update(budget_mesh=budget_mesh, sample_vertices=sample_vertices, path=path)
    eps = json.load(open(f'{path}/data/track_3_evaluation_objects.json'))['episodes']
    ro = {}
    for ep, names in eps.items():
        for slot, name in enumerate(names):
            ro.setdefault(name, []).append((int(ep), slot, _K['cdo']._object_seed(int(ep), slot)))
    t = json.load(open(f'{path}/config/tracks.json'))['tracks']['track_3']
    sym = {n: 'axial' for n in t['axially_symmetric_objects']}; sym.update({n: 'half' for n in t['half_turn_symmetric_objects']})
    _K.update(roster=ro, sym=sym)
    return _K


def load_candidate(path):
    """(vertices, faces) as the scorer decodes them (the kit packer's budget_mesh)."""
    v, f = kit()['budget_mesh'](path, BUDGET, BUDGET)
    return np.asarray(v, np.float64), np.asarray(f, np.int64)


def seeds_for(name):
    pairs = kit()['roster'].get(name, [])
    return [s for _, _, s in pairs] + list(EXTRA_SEEDS[:max(2, 6 - len(pairs))])


def rot_about(axis, angle):
    axis = np.asarray(axis, float) / np.linalg.norm(axis); x, y, z = axis
    Kx = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle) * Kx + (1 - math.cos(angle)) * Kx @ Kx


def angle_deg(R):
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))


def sym_axis(points, kind):
    """Among the PCA axes, the one the shape is most invariant under (90 deg turn for axial, 180 deg for half-turn)."""
    if kind is None:
        return None
    from scipy.spatial import cKDTree
    basis = kit()['auc']._pca_basis(points); ang = math.pi / 2 if kind == 'axial' else math.pi
    tree = cKDTree(points); best = None
    for k in range(3):
        d = tree.query(points @ rot_about(basis[:, k], ang).T)[0].mean()
        if best is None or d < best[0]:
            best = (d, basis[:, k].copy())
    return best[1]


def sym_rot_err(R, kind, axis):
    """Kit orientation error of a constant body rotation (AUC.py _symmetry_orientation_errors, static)."""
    if kind is None:
        return angle_deg(R)
    if kind == 'half':
        return min(angle_deg(R), angle_deg(R @ rot_about(axis, math.pi)))
    a = R @ axis
    return math.degrees(math.atan2(np.linalg.norm(np.cross(a, axis)), np.clip(a @ axis, -1, 1)))


def sym_group(kind, axis):
    auc = kit()['auc']
    if kind is None:
        return np.eye(3)[None]
    return auc._axial_rotations(axis, 2 if kind == 'half' else auc._SYMMETRY_ANGLES)


def add_static(da, R, q, group):
    """min over the symmetry group of mean |da + R^T q - S q| (AUC.py _symmetry_point_errors, constant offset)."""
    moved = q @ R + da; best = np.inf
    for S in group:
        best = min(best, float(np.linalg.norm(moved - q @ S.T, axis=1).mean()))
    return best


def flip_check(cand, ref, name):
    """X gate (xreg.py): {'xflips', 'n', 'xadd_med', 'seeds', 'pass'}."""
    K = kit(); auc = K['auc']
    bv, bf = load_candidate(ref); cv, cf = load_candidate(cand)
    anchor, _ = auc._surface_moments(bv, bf)
    q = K['sample_vertices'](ref) - anchor
    kind = K['sym'].get(name)
    axis = sym_axis(auc._sample_mesh_surface(bv, bf, 3000, 7) - anchor, kind); group = sym_group(kind, axis)
    rows = []
    for s in seeds_for(name):
        ca, Rm = auc._register_object_body((cv, cf), (bv, bf), anchor, s)
        err = sym_rot_err(Rm, kind, axis)
        rows.append(dict(seed=s, rot=round(err, 1), add_mm=round(add_static(ca - anchor, Rm, q, group) * 1e3, 2), flip=bool(err > 90)))
    nf = sum(r['flip'] for r in rows)
    return dict(xflips=nf, n=len(rows), xadd_med=float(np.median([r['add_mm'] for r in rows])), seeds=rows, **{'pass': nf == 0})


def consistency(cand, seed_mesh, seeds=(11, 22), thr_cm=0.5):
    """C gate (e0c_consistency.py): kit CD-O chamfer (Sim(3)) between the candidate and the tracking seed."""
    cdo = kit()['cdo']; a, b = load_candidate(seed_mesh), load_candidate(cand)
    d = [float(cdo._object_chamfer_cm(a, b, s)) for s in seeds]
    return dict(cd_cm=round(sum(d) / len(d), 3), per_seed=[round(x, 3) for x in d], **{'pass': sum(d) / len(d) <= thr_cm})


def registration_move(cand, ref, name, max_mm=2.0, max_deg=2.0):
    """G6 (xcheck.py form): rotation angle and mean point offset when the candidate is registered to ref."""
    K = kit(); auc = K['auc']; ref_m = load_candidate(ref); v, f = load_candidate(cand)
    anchor, _ = auc._surface_moments(*ref_m); q = auc._sample_mesh_surface(ref_m[0], ref_m[1], 500, 0) - anchor
    rows = []
    for s in seeds_for(name):
        ca, R = auc._register_object_body((v, f), ref_m, anchor, s)
        rows.append(dict(seed=s, rot=round(angle_deg(R), 2), off_mm=round(float(np.linalg.norm(q @ R + (ca - anchor) - q, axis=1).mean()) * 1e3, 2)))
    ok = all(r['rot'] <= max_deg and r['off_mm'] <= max_mm for r in rows)
    return dict(rot_max=max(r['rot'] for r in rows), off_max=max(r['off_mm'] for r in rows), seeds=rows, **{'pass': ok})


def topology(mesh):
    bodies = mesh.split(only_watertight=False)
    ok = all(b.is_watertight for b in bodies) and len(mesh.faces) <= BUDGET and len(mesh.vertices) <= BUDGET
    return dict(bodies=len(bodies), all_watertight=all(b.is_watertight for b in bodies), faces=len(mesh.faces),
                verts=len(mesh.vertices), euler=int(mesh.euler_number), **{'pass': bool(ok)})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('gate', choices=['flip', 'consistency', 'g6']); ap.add_argument('cand'); ap.add_argument('ref')
    ap.add_argument('object', nargs='?'); ap.add_argument('--kit')
    a = ap.parse_args()
    kit(a.kit)
    name = a.object or os.path.splitext(os.path.basename(a.ref))[0]
    r = {'flip': lambda: flip_check(a.cand, a.ref, name), 'consistency': lambda: consistency(a.cand, a.ref),
         'g6': lambda: registration_move(a.cand, a.ref, name)}[a.gate]()
    print(json.dumps(r))


if __name__ == '__main__':
    main()
