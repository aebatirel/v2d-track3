"""DIG 20 Stage C re-run: test of hypothesis C-[H]4 (a changepoint on the per-frame anchor POSE track, bounded by the
contact signal, beats the image-based MC window). Analysis only (public GT + simulated per-frame pose noise).
Per-frame estimate = GT pose of slot 0 x AR(1) noise (rho 0.7; rotation sigma_f deg, translation 2 mm per deg).
Windows (rows [0, end]):
  det  = stored MC detector window (GT-rendered mask; out/c/eval2_MC_A120_T2_L10_m3.json)
  cp   = causal changepoint on the noisy pose track: first k where 3 consecutive frames deviate from the running mean of
         frames [0, k) by > max(2 deg, 3 sigma_f) or > max(2 mm, 6 sigma_f mm); end = cp - 1
  cpC  = min(cp, contact_bc + 10) - 1  (contact from the stored detector)
  orr  = oracle [0, robust pert - 1];  cm1 = [0, 1 cm onset - 1];  f15 = [0, 14]
Error of the anchor = window mean of the noisy poses vs GT row 0 (rotation deg, translation mm).
usage: r_cpsim.py [nseed=40]"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import c_lib as L
from c_eval import gt
from scipy.spatial.transform import Rotation as Rot
OUT2 = f'{L.ROOT}/work/20/out/c2'
DET = {r['ep']: r for r in json.load(open(f'{L.OUT}/eval2_MC_A120_T2_L10_m3.json'))}
SYNC = json.load(open(f'{L.ROOT}/work/20/out/sync_table.json'))['episodes']


def ar1(rng, n, d, rho=0.7):
    e = rng.standard_normal((n, d)); x = np.zeros((n, d)); x[0] = e[0]
    for i in range(1, n): x[i] = rho * x[i - 1] + np.sqrt(1 - rho ** 2) * e[i]
    return x


def anchor_err(t, R, t0, R0, end):
    end = int(max(min(end, len(t) - 1), 0))
    tm = t[:end + 1].mean(0); Rm = R[:end + 1].mean()
    return float(np.degrees((Rm * R0.inv()).magnitude())), float(np.linalg.norm(tm - t0) * 1000), end + 1


def changepoint(t, R, sf, k0=3, w=3):
    thr_a = max(2.0, 3 * sf); thr_t = max(2.0, 6 * sf)
    run = 0
    for k in range(k0, len(t)):
        Rm = R[:k - run].mean() if k - run > 0 else R[0]; tm = t[:k - run].mean(0)
        da = np.degrees((R[k] * Rm.inv()).magnitude()); dt = np.linalg.norm(t[k] - tm) * 1000
        run = run + 1 if (da > thr_a or dt > thr_t) else 0
        if run >= w: return k - w + 1
    return len(t)


if __name__ == '__main__':
    nseed = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    res = {}
    for sf in (0.5, 1.0, 2.0, 3.0):
        acc = {k: [] for k in ('det', 'cp', 'cpC', 'orr', 'cm1', 'f15')}; cps = []
        for ep in L.PUB:
            g = gt(ep); P = g['e']['pose'][:, g['j']]; n = len(P)
            ok = np.isfinite(P).all(1); P = P[:np.argmin(ok) if not ok.all() else n]; n = len(P)
            t0, R0 = P[0, :3], Rot.from_quat(P[0, 3:])
            d = DET[ep]; nC = SYNC[f'p{ep}']['pairing_a_to_b'][0]['n']; Cbc = d['c'] - nC
            per = {k: [] for k in acc}
            for s in range(nseed):
                rng = np.random.default_rng(1000 * s + ep)
                nr = ar1(rng, n, 3) * np.radians(sf); nt = ar1(rng, n, 3) * sf * 0.002
                R = Rot.from_rotvec(nr) * Rot.from_quat(P[:, 3:]); t = P[:, :3] + nt
                cp = changepoint(t, R, sf); cps.append(cp - g['pert_r'])
                ends = dict(det=d['end'], cp=cp - 1, cpC=min(cp, Cbc + 10) - 1, orr=g['pert_r'] - 1, cm1=g['on'] - 1, f15=14)
                for k, e in ends.items(): per[k].append(anchor_err(t, R, t0, R0, e)[:2])
            for k in acc: acc[k].append(np.mean(per[k], 0))      # per-episode mean over seeds (rot deg, trans mm)
        res[sf] = {k: dict(rot_med=float(np.median(np.array(v)[:, 0])), rot_p90=float(np.percentile(np.array(v)[:, 0], 90)),
                           rot_max=float(np.max(np.array(v)[:, 0])), tr_med=float(np.median(np.array(v)[:, 1])),
                           tr_max=float(np.max(np.array(v)[:, 1]))) for k, v in acc.items()}
        res[sf]['cp_minus_pert_r'] = dict(median=float(np.median(cps)), p10=float(np.percentile(cps, 10)), p90=float(np.percentile(cps, 90)))
        print(f'sigma_f {sf} deg: cp - robust pert: median {np.median(cps):+.0f}, p10/p90 {np.percentile(cps, 10):+.0f}/{np.percentile(cps, 90):+.0f}')
        for k in acc:
            r = res[sf][k]
            print(f'   {k:4s} rot med/p90/max {r["rot_med"]:.2f}/{r["rot_p90"]:.2f}/{r["rot_max"]:.2f} deg | trans med/max {r["tr_med"]:.2f}/{r["tr_max"]:.2f} mm', flush=True)
    json.dump(res, open(f'{OUT2}/cpsim.json', 'w'), indent=1)
