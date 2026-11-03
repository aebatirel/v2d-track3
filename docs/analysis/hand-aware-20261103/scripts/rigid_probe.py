"""DIAGNOSTIC (3 Nov): headroom of a rigid-in-grasp prior on public episodes. Not an inference method yet: the hold runs
come from mocap (held_diag.json), and P0 reads mocap for its offset.
Per object and held run, contacting hand(s) = hands with >= 2 fingertips within CONTACT_CM of the TRACKED surface on
>= 50 % of the run's frames. Hand frame H(t) = Kabsch(palm points at the run's middle frame -> palm points at t), over
the PALM joints of every contacting hand (two hands = one rigid frame).
  P1 (GT-free given the run): T(t) = H(t) M1, M1 = robust mean over the run of H(t)^-1 T_track(t).
  P0 (oracle offset): T(t) = H(t) M0, M0 from mocap mapped into the track frame (A, Y fitted on rest frames; diagnostic).
  P1m: per frame, the midpoint (rotation slerp 0.5) of the track and P1.
Outside held runs every variant keeps the track. Writes <OUT>/<variant>/ep<e>/poses_world_vo.npz for score_registered.py.
Usage: rigid_probe.py T3 CTRL_DIR HANDS_DIR HELD_JSON LIB OUT EP..."""
import sys, os, json, numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
T3, CTRL, HANDS, HELD, LIB, OUT = sys.argv[1:7]; EPS = [int(x) for x in sys.argv[7:]]
PALM, TIPS, CONTACT_CM = [0, 1, 5, 9, 13, 17], [4, 8, 12, 16, 20], 3.0
held = json.load(open(HELD))


def kabsch(src, dst):
    cs, cd = src.mean(0), dst.mean(0); U, _, Vt = np.linalg.svd((src - cs).T @ (dst - cd))
    S = np.eye(3); S[2, 2] = np.sign(np.linalg.det(Vt.T @ U.T)); R = Vt.T @ S @ U.T
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = cd - R @ cs; return M


def rmean(Ms):                                    # robust mean of 4x4 rigid transforms (chordal rotation, median t)
    R = Rot.from_matrix(np.stack([m[:3, :3] for m in Ms])).mean().as_matrix()
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = np.median(np.stack([m[:3, 3] for m in Ms]), 0); return M


def T_of(p):
    M = np.eye(4); M[:3, :3] = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix(); M[:3, 3] = p[:3]; return M


report = {}
for e in EPS:
    P = dict(np.load(f'{CTRL}/ep{e}/poses_world_vo.npz')); names = list(P)
    hz = np.load(f'{HANDS}/ep{e}/hands_refined.npz')
    J = {s: hz[f'joints_{s}'].astype(float) for s in ('right', 'left')}; V = {s: hz[f'valid_{s}'] for s in ('right', 'left')}
    tab = pq.read_table(f'{T3}/ep{e}.parquet').to_pandas(); N = len(P[names[0]])
    out = {k: {n: P[n].copy() for n in names} for k in ('P1', 'P0', 'P1m', 'P2', 'P2m')}
    for n in names:
        r = held.get(f'{e}:{n}')
        if not r or not r['held_runs']: continue
        pts = trimesh.load(f'{LIB}/{n}.glb', force='mesh').sample(400, seed=0)
        G = np.stack([T_of([o['pose'] for o in tab['observation.objects'].iloc[f] if o['name'] == n][0]) for f in range(N)])
        rest = np.ones(N, bool)
        for a, b in r['held_runs']: rest[a:b] = False
        # A (mocap world -> track world) and Y (scan body -> template body) from rest frames, for P0 only
        if rest.sum() >= 5:
            Ys = [np.linalg.inv(G[t]) @ P[n][t] for t in np.nonzero(rest)[0]]   # with A ~ I: first pass
            A = np.eye(4)
            for _ in range(3):
                Y = rmean([np.linalg.inv(A @ G[t]) @ P[n][t] for t in np.nonzero(rest)[0]])
                A = rmean([P[n][t] @ np.linalg.inv(G[t] @ Y) for t in np.nonzero(rest)[0]])
            Ghat = np.stack([A @ G[t] @ Y for t in range(N)])
        else:
            Ghat = None
        for a, b in r['held_runs']:
            fr = np.arange(a, min(b, N))
            used = []
            for s in ('right', 'left'):
                c = 0
                for t in fr:
                    if not V[s][t]: continue
                    w = (P[n][t][:3, :3] @ pts.T).T + P[n][t][:3, 3]
                    d = np.linalg.norm(J[s][t][TIPS][:, None] - w[None], axis=-1).min(1) * 100
                    c += (d < CONTACT_CM).sum() >= 2
                if c >= 0.5 * len(fr): used.append(s)
            rep = dict(run=[int(a), int(b)], hands=used)
            if not used: report[f'{e}:{n}:{a}'] = rep; continue
            ok = np.array([all(V[s][t] for s in used) for t in fr]); fo = fr[ok]
            mid = fo[len(fo) // 2]; ref = np.concatenate([J[s][mid][PALM] for s in used])
            H = {t: kabsch(ref, np.concatenate([J[s][t][PALM] for s in used])) for t in fo}
            M1 = rmean([np.linalg.inv(H[t]) @ P[n][t] for t in fo])
            M0 = rmean([np.linalg.inv(H[t]) @ Ghat[t] for t in fo]) if Ghat is not None else None
            for t in fo:
                out['P1'][n][t] = H[t] @ M1
                if M0 is not None: out['P0'][n][t] = H[t] @ M0
                q = Rot.from_matrix(np.stack([P[n][t][:3, :3], (H[t] @ M1)[:3, :3]]))
                m = np.eye(4); m[:3, :3] = q.mean().as_matrix(); m[:3, 3] = 0.5 * (P[n][t][:3, 3] + (H[t] @ M1)[:3, 3])
                out['P1m'][n][t] = m
            # P2: track rotation, translation from the contacting hands' palm centroid + a constant object-frame offset
            cen = {t: np.concatenate([J[s][t][PALM] for s in used]).mean(0) for t in fo}
            mo = np.median(np.stack([P[n][t][:3, :3].T @ (P[n][t][:3, 3] - cen[t]) for t in fo]), 0)
            off = [np.linalg.norm(P[n][t][:3, :3].T @ (P[n][t][:3, 3] - cen[t]) - mo) * 100 for t in fo]
            rep['p2_offset_spread_cm_median'] = round(float(np.median(off)), 2)
            for t in fo:
                m = P[n][t].copy(); m[:3, 3] = cen[t] + P[n][t][:3, :3] @ mo; out['P2'][n][t] = m
                m2 = P[n][t].copy(); m2[:3, 3] = 0.5 * (m[:3, 3] + P[n][t][:3, 3]); out['P2m'][n][t] = m2
            # spread of the relative transform (how rigid is the grasp as our hands see it), on template points
            rel = [np.linalg.inv(H[t]) @ P[n][t] for t in fo]
            sp = [np.linalg.norm(((r_[:3, :3] - M1[:3, :3]) @ pts.T).T + r_[:3, 3] - M1[:3, 3], axis=1).mean() * 100 for r_ in rel]
            rep.update(frames=int(len(fo)), track_rel_spread_cm_median=round(float(np.median(sp)), 2))
            if Ghat is not None:
                relg = [np.linalg.inv(H[t]) @ Ghat[t] for t in fo]
                spg = [np.linalg.norm(((r_[:3, :3] - M0[:3, :3]) @ pts.T).T + r_[:3, 3] - M0[:3, 3], axis=1).mean() * 100 for r_ in relg]
                rep['gt_rel_spread_cm_median'] = round(float(np.median(spg)), 2)
            report[f'{e}:{n}:{a}'] = rep
    for k in out:
        os.makedirs(f'{OUT}/{k}/ep{e}', exist_ok=True); np.savez(f'{OUT}/{k}/ep{e}/poses_world_vo.npz', **out[k])
for k, v in report.items(): print(k, v)
json.dump(report, open(f'{OUT}/rigid_probe_report.json', 'w'), indent=1)
