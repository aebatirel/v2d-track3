"""Synthetic tests of tools/intrusion.py (two boxes with analytic overlaps, no overlap, fiducial / hash / provenance
refusals, the optional --fit residual). Run: venv/bin/python test_intrusion.py WORKDIR"""
import hashlib, importlib.util, json, os, shutil, sys
import numpy as np, pyarrow as pa, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot

TOOL = '/home/user/v2d-track3/tools/intrusion.py'
spec = importlib.util.spec_from_file_location('intrusion', TOOL); I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
W = os.path.abspath(sys.argv[1]); shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
mm = 1e-3; PITCH = 2 * mm
res = {}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def box(lo, hi):
    lo, hi = np.asarray(lo, float) * mm, np.asarray(hi, float) * mm
    m = trimesh.creation.box(extents=hi - lo); m.apply_translation((lo + hi) / 2); return m


TARGET = 'box_a'; PARTNER = 'box_b'
A_LO, A_HI = np.array([-50, -30, -20.]), np.array([50, 30, 20.])
B_EXT = np.array([80, 30, 20.])                                      # partner box, centred at its file origin
PIECES = {TARGET: [box([-50, -30, -20], [10, 30, 20]), box([10, -30, -20], [50, 30, 20])],   # abutting at x = 10 mm
          PARTNER: [box(-B_EXT / 2, B_EXT / 2)]}
Rz90 = Rot.from_euler('z', 90, degrees=True).as_matrix()
# partner centre in the target frame per frame (mm); None = far away
CENTRES = [(40.3, 0.7, 10.2), None, (0.3, 0.1, 30.0), (-45.2, 25.1, 0.3), (10.1, 0.3, 0.4)]


def make_sim(d, pieces=PIECES, manifest=True, fid_shift=None, recentre=False, episode=99):
    os.makedirs(d); man = dict(episode=episode, split='public', round=0, objects={})
    for n, ps in pieces.items():
        os.makedirs(f'{d}/{n}'); V = np.concatenate([p.vertices for p in ps])
        off = trimesh.util.concatenate(ps).center_mass if recentre else np.zeros(3)      # MuJoCo-style re-centring
        files = {}
        for k, p in enumerate(ps):
            q = p.copy(); q.apply_translation(-off); f = f'{d}/{n}/piece_{k:02d}.obj'; q.export(f); files[os.path.basename(f)] = sha(f)
        trimesh.util.concatenate(ps).export(f'{d}/{n}/{n}.glb')
        F = I.obb_fiducials(V) + (np.asarray(fid_shift) * mm if fid_shift is not None else 0)   # original file frame
        man['objects'][n] = dict(files=files, fiducials=F.tolist())
        os.makedirs(f'{d}/_fit', exist_ok=True); trimesh.util.concatenate(ps).export(f'{d}/_fit/{n}.glb')
    json.dump({n: dict(mass_kg=0.3) for n in pieces}, open(f'{d}/props_gmg.json', 'w'))
    if manifest:
        json.dump(man, open(f'{d}/manifest.json', 'w'), indent=1)
    return d


def poses(centres, fit_dx=None):
    """(T,2,4,4) target and partner world poses: target rotated differently each frame, partner = target @ rel."""
    T = len(centres); O = np.tile(np.eye(4), (T, 2, 1, 1)); rel = []
    for f, c in enumerate(centres):
        Rt = Rot.from_rotvec(np.array([0.3, -0.5, 0.8]) * (1 + 0.37 * f)).as_matrix()
        O[f, 0, :3, :3] = Rt; O[f, 0, :3, 3] = [0.1 + 0.01 * f, -0.2, 0.7]
        Rl = np.eye(4); Rl[:3, :3] = Rz90; Rl[:3, 3] = (np.array(c) if c is not None else np.array([400.0, 0, 0])) * mm
        if fit_dx is not None and f in fit_dx:
            Rl[:3, 3] += np.asarray(fit_dx[f]) * mm
        rel.append(Rl); O[f, 1] = O[f, 0] @ Rl
    return O, np.array(rel)


def write_ref(path, O, names=(TARGET, PARTNER)):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    q = Rot.from_matrix(O[..., :3, :3].reshape(-1, 3, 3)).as_quat()[:, [3, 0, 1, 2]].reshape(O.shape[0], O.shape[1], 4)
    t = pa.table(dict(object_body_names=[list(names)], object_body_position=[O[..., :3, 3].tolist()],
                      object_body_wxyz=[q.tolist()], fps=[20.0]))
    pq.write_table(t, path); return path


def run(args):
    try:
        return I.main(args), None
    except SystemExit as e:
        return None, str(e)


def lattice_count(c, lo, hi):
    """Independent count: partner lattice points (i + 1/2) pitch strictly inside the partner box, mapped by Rz90 + c,
    strictly inside the target box [lo, hi] (mm)."""
    ax = [(np.arange(np.floor(-e / 2 / 2 - .5), np.ceil(e / 2 / 2 - .5) + 1) + .5) * 2 for e in B_EXT]
    G = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3); G = G[np.all(np.abs(G) < B_EXT / 2 - 1e-3, 1)]
    X = G @ Rz90.T + np.asarray(c)
    return int(np.all((X > lo + 1e-3) & (X < hi - 1e-3), 1).sum()), X, G


def overlap_box(c):
    h = (np.abs(Rz90) @ B_EXT) / 2; lo, hi = np.maximum(A_LO, np.asarray(c) - h), np.minimum(A_HI, np.asarray(c) + h)
    return lo, hi, float(np.prod(np.clip(hi - lo, 0, None)))


# ---------------------------------------------------------------- 1. two boxes, known overlaps
sim = make_sim(f'{W}/sim1/r0'); O, rel = poses(CENTRES)
ref = write_ref(f'{W}/ref1/processed/sequence_id=t3_ep099/robot_name=sharpa_wave/ref.parquet', O)
for f in ('poses.npz', 'poses_world_vo.npz', 'hands_refined.npz', 'table_frame.npz'):
    open(f'{W}/ref1/{f}', 'wb').write(os.urandom(64))
prov = dict(chain=[dict(tool='pipeline/mkref.py', commit='0' * 40, run_id='20261031-test-0000000', artifact=ref, sha256=sha(ref),
                        inputs={f'{W}/ref1/{f}': sha(f'{W}/ref1/{f}') for f in ('poses.npz', 'poses_world_vo.npz', 'hands_refined.npz', 'table_frame.npz')})])
json.dump(prov, open(f'{W}/prov1.json', 'w'))
hdr, err = run([ref, sim, f'{W}/out1/intrusions.npz', '--prov', f'{W}/prov1.json'])
assert err is None, err
Z = np.load(f'{W}/out1/intrusions.npz'); H = json.load(open(f'{W}/out1/intrusions.json'))
case = {}
for f, c in enumerate(CENTRES):
    rows = np.nonzero((Z['fp_frame'] == f) & (Z['fp_target'] == 0) & (Z['fp_partner'] == 1))[0]
    if c is None:
        case[f] = dict(rows=len(rows)); assert len(rows) == 0; continue
    r = rows[0]; s = (Z['frame'] == f) & (Z['target'] == 0) & (Z['partner'] == 1); X = Z['pts_local'][s].astype(float) / mm
    lo, hi, v = overlap_box(c); n_exp, _, _ = lattice_count(c, A_LO, A_HI)
    relT_exp = np.linalg.inv(O[f, 0]) @ O[f, 1]
    back = (X * mm) @ np.linalg.inv(Z['rel_T'][r])[:3, :3].T + np.linalg.inv(Z['rel_T'][r])[:3, 3]
    lat_err = np.abs(back / PITCH - 0.5 - np.round(back / PITCH - 0.5)).max() * PITCH / mm if len(X) else 0
    true_d = np.min(np.c_[50 - np.abs(X[:, 0]), 30 - np.abs(X[:, 1]), 20 - np.abs(X[:, 2])], 1) if len(X) else np.zeros(0)
    dm, dl = Z['depth_m'][s] / mm, Z['depth_lb_m'][s] / mm
    case[f] = dict(analytic_cm3=v * 1e-3, export_cm3=float(Z['intr_vol_m3'][r] * 1e6), n=int(s.sum()), n_expected_lattice=n_exp,
                   pts_outside_overlap_mm=float(np.max(np.r_[0, (lo - X).max(1) if len(X) else 0, (X - hi).max(1) if len(X) else 0])),
                   partner_lattice_err_mm=float(lat_err), rel_T_err=float(np.abs(Z['rel_T'][r] - relT_exp).max()),
                   depth_err_mm=[float((dm - true_d).min()) if len(X) else 0, float((dm - true_d).max()) if len(X) else 0],
                   depth_lb_below_true_mm=float((true_d - dl).max()) if len(X) else 0, depth_lb_over_true_mm=float((dl - true_d).max()) if len(X) else 0)
    assert case[f]['n'] == n_exp, case[f]
    assert case[f]['pts_outside_overlap_mm'] < 1e-3 and lat_err < 1e-3 and case[f]['rel_T_err'] < 1e-9, case[f]
    if len(X):
        assert -1e-3 < case[f]['depth_err_mm'][0] and case[f]['depth_err_mm'][1] < 0.71 * 0.5 + 1e-3, case[f]
        assert case[f]['depth_lb_over_true_mm'] < 1e-3, case[f]
        e = np.clip(hi - lo, 0, None); bound = (e[0] * e[1] + e[1] * e[2] + e[0] * e[2]) * 2 * 1.0 * 1e-3   # area x pitch/2, cm3
        case[f]['lattice_bound_cm3'] = bound; case[f]['rel_err'] = case[f]['export_cm3'] / case[f]['analytic_cm3'] - 1
        assert abs(case[f]['export_cm3'] - case[f]['analytic_cm3']) <= bound, case[f]
assert case[4]['depth_lb_below_true_mm'] > 5, 'abutting pieces: lower bound should miss depth across the cut'
assert H['f_star'] == int(np.argmax([case[f].get('export_cm3', 0) for f in range(len(CENTRES))]))
assert H['reference']['provenance']['complete'] and 'reference_provenance_incomplete' not in H['flags']
assert H['checks']['fiducial_round_trip_mm'] < 1e-6 and H['checks']['containment_target'] == 1 and H['checks']['containment_partner'] == 1
assert np.all(np.isnan(Z['pushed_residual_m'])) and H['fit'] is None and H['schema'] == 'gmg-intrusion/2'
# reverse pair (target = box_b): volume symmetric
rv = [float(Z['intr_vol_m3'][(Z['fp_frame'] == f) & (Z['fp_target'] == 1)].sum() * 1e6) for f in (0, 3, 4)]
res['1_two_boxes'] = dict(frames=case, reverse_pair_cm3=rv, f_star=H['f_star'], checks=H['checks'], seconds=H['seconds'],
                          counts=H['counts'], flags=H['flags'])

# ---------------------------------------------------------------- 2. no overlap (far, and touching faces)
O2, _ = poses([None, (0.3, 0.1, 30.0), (0.3, 0.1, 30.0), None])
ref2 = write_ref(f'{W}/ref2/processed/sequence_id=t3_ep099/robot_name=sharpa_wave/ref.parquet', O2)
hdr, err = run([ref2, sim, f'{W}/out2/intrusions.npz']); assert err is None, err
Z2 = np.load(f'{W}/out2/intrusions.npz'); H2 = json.load(open(f'{W}/out2/intrusions.json'))
assert len(Z2['pts_local']) == 0 and np.all(Z2['intr_vol_m3'] == 0)
assert any('no_intrusion' in f for f in H2['flags']) and 'reference_provenance_incomplete' in H2['flags']
res['2_no_overlap'] = dict(samples=len(Z2['pts_local']), rows=len(Z2['fp_frame']), flags=H2['flags'],
                           provenance_missing=H2['reference']['provenance']['missing'],
                           perception_absent=H2['reference']['provenance']['perception_absent'])

# ---------------------------------------------------------------- 3. fiducial failures
OFF = {n: [p.copy().apply_translation(np.array([7.0, -3.0, 2.0]) * mm) for p in ps] for n, ps in PIECES.items()}  # origin off the COM
sim3 = make_sim(f'{W}/sim3/r0', pieces=OFF, recentre=True)          # pieces re-centred, manifest hashes match them
_, e3 = run([ref, sim3, f'{W}/out3/intrusions.npz']); assert e3 and 'fiducials do not match' in e3, e3
sim3b = make_sim(f'{W}/sim3b/r0', fid_shift=(0, 2.0, 0))            # stale fiducials shifted 2 mm
_, e3b = run([ref, sim3b, f'{W}/out3b/intrusions.npz']); assert e3b and 'fiducials do not match' in e3b, e3b
orig = I.inv_pose                                                    # a tool whose pts_local inverse is off by 1 mm


def bad_inv(O):
    Oi = orig(O); Oi[..., 0, 3] += 1e-3; return Oi


I.inv_pose = bad_inv
_, e3c = run([ref, sim, f'{W}/out3c/intrusions.npz']); I.inv_pose = orig
assert e3c and 'round trip' in e3c, e3c
assert not os.path.exists(f'{W}/out3/intrusions.npz') and not os.path.exists(f'{W}/out3c/intrusions.npz')
res['3_fiducial_failure'] = dict(recentred=e3[:220], shifted_2mm=e3b[:220], wrong_inverse=e3c)

# ---------------------------------------------------------------- 4. hash mismatch, episode mismatch, denied inputs
sim4 = make_sim(f'{W}/sim4/r0'); open(f'{sim4}/{TARGET}/piece_00.obj', 'a').write('# edited\n')
_, e4 = run([ref, sim4, f'{W}/out4/intrusions.npz']); assert e4 and 'differ' in e4, e4
sim4b = make_sim(f'{W}/sim4b/r0', episode=24)
_, e4b = run([ref, sim4b, f'{W}/out4b/intrusions.npz']); assert e4b and 'episode' in e4b, e4b
refm = write_ref(f'{W}/mocap_arm/processed/sequence_id=t3_ep099/robot_name=sharpa_wave/ref.parquet', O)
_, e4c = run([refm, sim, f'{W}/out4c/intrusions.npz']); assert e4c and 'denied' in e4c, e4c
pv = dict(chain=[dict(tool='pipeline/mkref.py', commit='1' * 40, run_id='x', artifact=ref, sha256=sha(ref),
                      inputs={'/x/meshes/library_v3/wooden_piece_1.glb': None})])
json.dump(pv, open(f'{W}/prov_bad.json', 'w'))
_, e4d = run([ref, sim, f'{W}/out4d/intrusions.npz', '--prov', f'{W}/prov_bad.json']); assert e4d and 'denied' in e4d, e4d
_, e4e = run([ref, sim, f'{W}/out1/intrusions.npz']); assert e4e and 'never overwritten' in e4e
res['4_refusals'] = dict(hash=e4[:160], episode=e4b, mocap_ref=e4c[:160], library_in_chain=e4d[:200], overwrite=e4e[:120])

# ---------------------------------------------------------------- 5. --fit: residual on the fit's poses
fin, fout = f'{W}/fit/in', f'{W}/fit/out'; os.makedirs(fin); os.makedirs(fout)
np.savez(f'{fin}/table_frame.npz', T_table_from_world=np.eye(4), names=np.array([TARGET, PARTNER]), object_z_shift=np.zeros(2), table_z=0.6)
np.savez(f'{fin}/poses_world_vo.npz', **{TARGET: O[:, 0], PARTNER: O[:, 1]})
np.savez(f'{fin}/poses.npz', world_T_cam=np.tile(np.eye(4), (len(O), 1, 1)))
Of, _ = poses(CENTRES, fit_dx={0: (5.0, 0, 0)})                     # the fit moves the partner 5 mm out along target x
np.savez(f'{fout}/poses_world_vo.npz', **{TARGET: Of[:, 0], PARTNER: Of[:, 1]})
args = dict(inp=fin, out=fout, meshes=f'{sim}/_fit', props=f'{sim}/props_gmg.json', fps=20.0, w_dyn=1.0, sig_p=0.01, sig_r_deg=3.0,
            max_nfev=60, hold_f0=0)
json.dump(dict(args=args, objects={}), open(f'{fout}/phys_fit.json', 'w'))
hdr, err = run([ref, sim, f'{W}/out5/intrusions.npz', '--fit', fout, '--fit_commit', 'f' * 40]); assert err is None, err
Z5 = np.load(f'{W}/out5/intrusions.npz'); H5 = json.load(open(f'{W}/out5/intrusions.json'))
r0 = np.nonzero((Z5['fp_frame'] == 0) & (Z5['fp_target'] == 0))[0][0]
c = np.array(CENTRES[0]) + [5.0, 0, 0]; _, Xl, _ = lattice_count(c, A_LO, A_HI)
exp_lat = min(50 - Xl[:, 0].min(), 20 - Xl[:, 2].min())               # lattice MTD: clear the +x or +z face
lo, hi, _ = overlap_box(c); exp_geo = min(A_HI[0] - lo[0], A_HI[2] - lo[2])
pr = Z5['pushed_residual_m'] / mm
assert H5['fit']['used'] and not np.isnan(pr).any() and abs(pr[r0] - exp_lat) < 0.3, (pr[r0], exp_lat, H5['fit'])
# the same fit on scan meshes is refused; on non-round meshes it stays NaN
args2 = dict(args, meshes=f'{W}/scanlib2'); os.makedirs(f'{W}/scanlib2')
for n in PIECES:
    shutil.copy(f'{sim}/_fit/{n}.glb', f'{W}/scanlib2/{n}.glb')
fout2 = f'{W}/fit/out_s'; shutil.copytree(fout, fout2); json.dump(dict(args=args2), open(f'{fout2}/phys_fit.json', 'w'))
_, e5 = run([ref, sim, f'{W}/out5b/intrusions.npz', '--fit', fout2]); assert e5 and 'denied' in e5, e5
fout3 = f'{W}/fit/out_other'; shutil.copytree(fout, fout3); os.makedirs(f'{W}/other_meshes')
for n in PIECES:
    shutil.copy(f'{sim}/_fit/{n}.glb', f'{W}/other_meshes/{n}.glb')
json.dump(dict(args=dict(args, meshes=f'{W}/other_meshes')), open(f'{fout3}/phys_fit.json', 'w'))
hdr, err = run([ref, sim, f'{W}/out5c/intrusions.npz', '--fit', fout3]); assert err is None, err
Z5c = np.load(f'{W}/out5c/intrusions.npz'); H5c = json.load(open(f'{W}/out5c/intrusions.json'))
assert np.isnan(Z5c['pushed_residual_m']).all() and 'fit_meshes_not_round_fit' in H5c['flags'] and 'fit_commit_unknown' in H5c['flags']
res['5_fit'] = dict(residual_mm=float(pr[r0]), expected_lattice_mm=float(exp_lat), expected_geometric_mm=float(exp_geo),
                    residual_other_rows_mm=np.round(pr, 2).tolist(), fit_seconds=H5['seconds']['fit'],
                    input_vs_reference=H5['fit']['input_vs_reference'], scan_fit=e5[:160], other_meshes_flags=H5c['flags'])
json.dump(res, open(f'{W}/results.json', 'w'), indent=1, default=float)
print(json.dumps(res, indent=1, default=float)); print('ALL PASS')
