"""posefix measurement (GT-free): per object and frame, hand distance and table height; per pair and frame,
penetration depth and overlap volume of our visual meshes at our tracked poses.

Usage: python -I pf_measure.py TRACKS_ROOT OUT_DIR EP [EP ...]
  TRACKS_ROOT/ep<e>/poses_world_vo.npz (4x4 world_vo poses per object). Writes OUT_DIR/ep<e>_measure.npz + .json.
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_lib as L

HAND_M = 0.030           # H30: no hand joint within 30 mm of the object's mesh surface


def measure(P, names, sdfs, n_tab, d_tab, J):
    T = len(P[names[0]])
    out = {}
    for o in names:
        sd = sdfs[o]
        hd = np.full(T, np.inf); hmin = np.zeros(T)
        for t in range(T):
            M = P[o][t]
            if len(J[t]):
                Xl = L.tf(L.inv(M), J[t])
                dist = sd.surf_dist(Xl)
                ins = sd.query(Xl) < 0
                dist = np.where(ins, 0.0, dist)
                hd[t] = dist.min()
            hmin[t] = (L.tf(M, sd.probes) @ n_tab + d_tab).min()
        out[f'hand_mm/{o}'] = hd * 1000
        out[f'table_min_mm/{o}'] = hmin * 1000
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            dab = np.zeros(T); dba = np.zeros(T); vol = np.zeros(T); gap = np.zeros(T)
            small, big = (a, b) if sdfs[a].volume_cm3 <= sdfs[b].volume_cm3 else (b, a)
            for t in range(T):
                Ma, Mb = P[a][t], P[b][t]
                Tab = L.inv(Mb) @ Ma                                    # a local -> b local
                sa = sdfs[b].query(L.tf(Tab, sdfs[a].probes))
                sb = sdfs[a].query(L.tf(L.inv(Tab), sdfs[b].probes))
                dab[t] = max(0.0, -sa.min()); dba[t] = max(0.0, -sb.min())
                gap[t] = max(0.0, min(sa.min(), sb.min()))
                Ts = L.inv(P[big][t]) @ P[small][t]
                vol[t] = float((sdfs[big].query(L.tf(Ts, sdfs[small].inside_nodes)) < 0).sum()) * L.GRID_H ** 3 * 1e6
            out[f'depth_mm/{a}|{b}'] = dab * 1000          # a's probes inside b
            out[f'depth_mm/{b}|{a}'] = dba * 1000
            out[f'overlap_cm3/{a}|{b}'] = vol
            out[f'gap_mm/{a}|{b}'] = gap * 1000            # > 0: separated by at least this (probe-based)
    return out


if __name__ == '__main__':
    root, od = sys.argv[1], sys.argv[2]
    os.makedirs(od, exist_ok=True)
    sdfs = {}
    for e in [int(x) for x in sys.argv[3:]]:
        t0 = time.time()
        P = np.load(f'{root}/ep{e}/poses_world_vo.npz')
        names = list(P.files)
        P = {n: np.asarray(P[n], np.float64) for n in names}
        for n in names:
            if n not in sdfs:
                sdfs[n] = L.SDF(n, *L.load_mesh(n))
        n_tab, d_tab = L.table_plane(e)
        J = L.hands(e)
        out = measure(P, names, sdfs, n_tab, d_tab, J)
        np.savez(f'{od}/ep{e}_measure.npz', names=np.array(names), **out)
        print(e, names, f'{time.time() - t0:.1f} s', flush=True)
