"""ORACLE DIAGNOSTIC (public episodes only): rollout-level split of RPE / MPPE / AUC into reference error and policy
error, on per-draw evaluator rollouts (flash_chord parquets: achieved = simulated object, reference = the reference the
policy tracked; both are library_v3 body-frame poses in the table frame).
Per draw, all in the kit's registered chain (lib convention, rdlib):
  total   sim vs mocap        (what the leaderboard scores)
  ref     reference vs mocap  (reference error; identical in every draw of one checkpoint)
  policy  sim vs reference    (rollout-vs-reference error: the reference treated as truth, with library_v3 as both the
                               submitted and the host mesh: anchor = its surface centroid, 1000 samples, identity
                               registration; cups / lid get their library-mesh symmetry axis)
Reads ground truth (mocap, scans).
Usage: python -I roll.py RDLIB_DIR SCRATCH OUT_JSON ROOT:ARM:EP [ROOT:ARM:EP ...]   (ROOT/ARM/epN/r*/episode_0000NN.parquet)
"""
import glob, json, os, sys, time
import numpy as np, pyarrow.parquet as pq

sys.path.insert(0, sys.argv[1])
import rdlib as L
LIB = '/home/user/v2d-track3/meshes/library_v3'


def load(f, names):
    t = pq.read_table(f).to_pandas()
    t = t[t.environment_id == t.environment_id.min()]
    fr = np.sort(t.reference_frame.unique()); B = len(names)
    A = np.full((len(fr), B, 7), np.nan); F = np.full((len(fr), B, 7), np.nan)
    idx = {n: i for i, n in enumerate(names)}
    for row in t.itertuples():
        i = np.searchsorted(fr, row.reference_frame); s = idx[row.object_body_name]
        A[i, s] = [row.achieved_position_x, row.achieved_position_y, row.achieved_position_z, row.achieved_quaternion_x,
                   row.achieved_quaternion_y, row.achieved_quaternion_z, row.achieved_quaternion_w]
        F[i, s] = [row.reference_position_x, row.reference_position_y, row.reference_position_z, row.reference_quaternion_x,
                   row.reference_quaternion_y, row.reference_quaternion_z, row.reference_quaternion_w]
    assert np.isfinite(A).all() and np.isfinite(F).all() and (fr == np.arange(len(fr))).all(), f
    return A, F


def lib_host(n, slot):  # library_v3 as host geometry (for sim vs reference)
    v, f = L.load_vf(f'{LIB}/{n}.glb'); c, r = L.M._surface_moments(v, f)
    pts = L.M._sample_mesh_surface(v, f, 1000, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in L.SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if L.SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
    return dict(name=n, mesh=(v, f), anchor=c, radius=r, points=pts, axis=axis, order=order)


def main():
    rd, scratch, out = sys.argv[1:4]
    L.load_kit(f'{scratch}/dl/kit/v2d_submission_kit'); t3 = f'{scratch}/t3'
    res = {}
    for spec in sys.argv[4:]:
        root, arm, ep = spec.split(':'); ep = int(ep); L.guard(ep); t0 = time.time()
        names = L.names_of(t3, ep)
        H = [L.host_geometry(t3, n, s) for s, n in enumerate(names)]
        Hl = [lib_host(n, s) for s, n in enumerate(names)]
        REG = [L.kit_reg(LIB, n, H[s], ep, s) for s, n in enumerate(names)]
        REGl = [(h['anchor'], np.eye(3)) for h in Hl]
        draws = sorted(glob.glob(f'{root}/{arm}/ep{ep}/r*/episode_{ep:06d}.parquet'), key=lambda p: int(p.split('/r')[-1].split('/')[0]))
        rows = []; ref_m = None
        for f in draws:
            A, F = load(f, names)
            G = L.ref_anchor(L.mocap7(t3, ep, names, len(A)), H)          # GROUND TRUTH
            tot = L.score(L.convert(A, REG), G, H, per_frame=True)
            if ref_m is None:
                ref_m = L.score(L.convert(F, REG), G, H, per_frame=True); F0 = F
            same = bool(np.allclose(F, F0, atol=1e-6))
            pol = L.score(L.convert(A, REGl), L.ref_anchor(F, Hl), Hl)
            qa = json.load(open(os.path.join(os.path.dirname(f), 'qa_policy.json'))) if os.path.exists(os.path.join(os.path.dirname(f), 'qa_policy.json')) else {}
            rows.append(dict(draw=f.split('/')[-2], same_reference=same, sim_vs_ref_qa=qa.get('sim_vs_ref'),
                             total={k: round(tot[k], 4) for k in ('AUC', 'MPPE', 'RPE')},
                             total_obj_MPPE=[round(x, 4) for x in tot['obj_MPPE']],
                             policy={k: round(pol[k], 4) for k in ('AUC', 'MPPE', 'RPE')},
                             rpe_max_frame_cm=round(float(tot['pf_rpe_cm'].max()), 2),
                             rpe_frac_frames_over_5cm=round(float((tot['pf_rpe_cm'] > 5).mean()), 3)))
        mean = lambda key, k: round(float(np.mean([r[key][k] for r in rows])), 4)
        res[f'{arm}/ep{ep}'] = dict(arm=arm, ep=ep, names=names, n_draws=len(rows),
                                     reference={k: round(ref_m[k], 4) for k in ('AUC', 'MPPE', 'RPE')},
                                     reference_obj_MPPE=[round(x, 4) for x in ref_m['obj_MPPE']],
                                     total_mean={k: mean('total', k) for k in ('AUC', 'MPPE', 'RPE')},
                                     policy_mean={k: mean('policy', k) for k in ('AUC', 'MPPE', 'RPE')},
                                     draws=rows)
        r = res[f'{arm}/ep{ep}']
        print(f'{arm} ep{ep}: n={len(rows)} ref RPE {r["reference"]["RPE"]:.2f} MPPE {r["reference"]["MPPE"]:.2f} AUC {r["reference"]["AUC"]:.3f} | '
              f'total RPE {r["total_mean"]["RPE"]:.2f} MPPE {r["total_mean"]["MPPE"]:.2f} AUC {r["total_mean"]["AUC"]:.3f} | '
              f'policy RPE {r["policy_mean"]["RPE"]:.2f} MPPE {r["policy_mean"]["MPPE"]:.2f} AUC {r["policy_mean"]["AUC"]:.3f} ({time.time() - t0:.0f} s)', flush=True)
    json.dump(dict(kind='rpe-decomp rollouts', note='ORACLE DIAGNOSTIC, public episodes only.', cells=res), open(out, 'w'), indent=1)
    print('wrote', out)


if __name__ == '__main__':
    main()
