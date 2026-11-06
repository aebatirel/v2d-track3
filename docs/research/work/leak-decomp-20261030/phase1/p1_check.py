"""ORACLE DIAGNOSTIC (public episodes only): checks on the Phase-1 tracks before the leak readings (PLAN.md §3 Phase 1;
JOBS.txt "After the boxes" 2). Reads GROUND TRUTH (public mocap and scans); nothing here feeds eval inference.
  camera   every P_o arm's world_T_cam (perc2/poses.npz) vs the refine inputs' (the hands were made on that camera;
           expect <= 1e-6 m): max abs entry, translation (m) and rotation (deg) over frames.
  repeat   P_o vs the P_o repeat (same box, commit, depth cache): max and mean pose difference per object (cm, deg).
  drift    P_o vs the refine-baseline P (refine/in, 25 Oct tracks, library_v2 templates): same, per object.
  native   R*(P_s) in native scan frames: the scan-template track scored with the scan as the submitted mesh and the
           identity registration (the kit chain of tools/xstar_fit.py score_track); must equal the * column of the
           P_s track taken to lib frames by X*_geom (frame invariance, PLAN §7 (b): <= 0.002). Beside it, perc2's own
           scan-frame vo AUC from the job's summary.json (another scorer: no rule).
Usage: python -I p1_check.py --roots ROOTS --refine REFINE_IN --t3 T3 --kit KIT --summaries S1,S2,S3 --out JSON
       (ROOTS/{Po,Po2,Ps_scan}/ep<N>/poses_world_vo.npz, ROOTS/Po/ep<N>/poses.npz; ROOTS must contain 'oracle')
(2026-10-30)
"""
import argparse, json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import xstar_fit as XF  # noqa: E402


def pose_diff(A, B):  # (N,4,4) x2 -> max/mean translation cm, max/mean rotation deg
    t = np.linalg.norm(A[:, :3, 3] - B[:, :3, 3], axis=1) * 100
    r = np.degrees(Rot.from_matrix(np.einsum('nji,njk->nik', A[:, :3, :3], B[:, :3, :3])).magnitude())
    return dict(t_max_cm=round(float(t.max()), 4), t_mean_cm=round(float(t.mean()), 4),
                r_max_deg=round(float(r.max()), 3), r_mean_deg=round(float(r.mean()), 3))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--roots', required=True); p.add_argument('--refine', required=True); p.add_argument('--t3', required=True)
    p.add_argument('--kit', required=True); p.add_argument('--summaries', required=True); p.add_argument('--out', required=True)
    a = p.parse_args()
    if os.environ.get('SPLIT', 'public') != 'public' or 'oracle' not in os.path.abspath(a.roots):
        sys.exit('public episodes only; ROOTS must contain "oracle"')
    XF.kit(a.kit)
    vo_auc = {}
    for f in a.summaries.split(','):
        for ep, e in json.load(open(f))['episodes'].items():
            vo_auc[int(ep[2:])] = e.get('s_vo_auc_scan_frame')
    eps = sorted(int(d[2:]) for d in os.listdir(f'{a.roots}/Po'))
    bad = [e for e in eps if e in XF.EVAL]
    if bad:
        sys.exit(f'eval episodes {bad}: public episodes only')
    res = {}
    for ep in eps:
        r = {}
        W = np.load(f'{a.roots}/Po/ep{ep}/poses.npz')['world_T_cam']; W0 = np.load(f'{a.refine}/ep{ep}/poses.npz')['world_T_cam']
        r['camera_vs_refine'] = dict(frames=[len(W), len(W0)], max_abs=float(np.abs(W - W0).max()) if W.shape == W0.shape else None,
                                     **(pose_diff(W, W0) if W.shape == W0.shape else {}))
        V = np.load(f'{a.roots}/Po/ep{ep}/poses_world_vo.npz'); V0 = np.load(f'{a.refine}/ep{ep}/poses_world_vo.npz')
        r['drift_vs_refine'] = {n: pose_diff(V[n], V0[n]) for n in V.files}
        if os.path.exists(f'{a.roots}/Po2/ep{ep}/poses_world_vo.npz'):
            V2 = np.load(f'{a.roots}/Po2/ep{ep}/poses_world_vo.npz')
            r['repeat'] = {n: dict(identical=bool(np.array_equal(V[n], V2[n])), **pose_diff(V[n], V2[n])) for n in V.files}
        S = np.load(f'{a.roots}/Ps_scan/ep{ep}/poses_world_vo.npz')
        names, gt = XF.mocap(a.t3, ep, len(S[S.files[0]]))
        if sorted(names) != sorted(S.files):
            sys.exit(f'ep{ep}: P_s names {S.files} != slots {names}')
        H = [XF.host_geometry(a.t3, n, s) for s, n in enumerate(names)]
        sc = XF.score_track(names, {n: S[n].astype(np.float64) for n in names}, gt, H, [XF.reg_of_X(np.eye(4), h['anchor']) for h in H])
        r['Ps_native_star'] = sc; r['Ps_perc2_vo_auc_scan_frame'] = vo_auc.get(ep)
        res[str(ep)] = r
        print(f'ep{ep}: camera vs refine max {r["camera_vs_refine"]["max_abs"]:.2e}  P_s native * {sc["AUC"]:.4f} (perc2 '
              f'{vo_auc.get(ep, float("nan")):.4f})' + (f'  repeat identical {[v["identical"] for v in r["repeat"].values()]}'
                                                        if 'repeat' in r else ''), flush=True)
    out = dict(note='ORACLE DIAGNOSTIC (public episodes; mocap and scans). Phase-1 track checks; see the docstring of p1_check.py.',
               roots=os.path.abspath(a.roots), refine=os.path.abspath(a.refine), episodes=res)
    json.dump(out, open(a.out, 'w'), indent=1)
    print(f'wrote {a.out}')


if __name__ == '__main__':
    main()
