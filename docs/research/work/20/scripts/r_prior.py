"""DIG 20 Stage C re-run: per-object size/colour priors for GT-free slot-0 blob selection (public GT used as a PRIOR).
Per public ep and object at row 0: height of the top above the table (z99 of surface samples - 0.601 m), footprint
extents l1 >= l2 (1-99 % PCA extents of the xy samples), and the mean cam-a chroma (Lab a*, b*) inside the eroded
GT-rendered mask (D18 frame-0 camera; 19 eps). The spoon (no public GT) gets mesh-only values (note 13 dimensions).
usage: r_prior.py  -> out/c2/prior_obj.json"""
import sys, os, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import c_lib as L
import c11
OUT2 = f'{L.ROOT}/work/20/out/c2'
TABLE_Z = 0.601


def dims_world(name, pose7):
    P = c11.surface_points(name, 3000)
    X = P @ c11.R_of(pose7[3:]).T + pose7[:3]
    h = float(np.percentile(X[:, 2], 99) - TABLE_Z)
    xy = X[:, :2] - X[:, :2].mean(0); _, _, vt = np.linalg.svd(xy, full_matrices=False); u = xy @ vt.T
    ext = np.percentile(u, 99, 0) - np.percentile(u, 1, 0)
    return h, float(max(ext)), float(min(ext))


if __name__ == '__main__':
    out = {}
    for ep in L.PUB + [45]:
        if os.environ.get('SKIP_PUB'): break
        e = c11.load_episode(ep)
        F0 = L.frames('public', ep, 'a', n_max=1)[0] if ep in L.PUB else None
        for j, name in enumerate(e['names']):
            p = e['pose'][0, j]
            if not np.isfinite(p).all(): continue
            h, l1, l2 = dims_world(name, p)
            rec = dict(ep=ep, h=h, l1=l1, l2=l2)
            if F0 is not None:
                R, C = L.cam0(ep); M, z = L.silhouette(name, p, R, C)
                Me = cv2.erode(M, np.ones((9, 9), np.uint8)) > 0
                if Me.sum() > 200:
                    lab = cv2.cvtColor(F0, cv2.COLOR_BGR2LAB).astype(float)
                    rec['ab'] = [float(np.median(lab[..., 1][Me])), float(np.median(lab[..., 2][Me]))]
                    rec['Lum'] = float(np.median(lab[..., 0][Me]))
            out.setdefault(name, []).append(rec)
            print(ep, name, json.dumps(rec), flush=True)
    # spoon: no public scan or GT. Note 13: wood length ~30 cm, bowl width ~5.2 cm; resting height ~3 cm with markers [E]
    out['wooden_spoon'] = [dict(ep=-1, h=0.03, l1=0.30, l2=0.055, ab=[130.0, 150.0])]
    json.dump(out, open(f'{OUT2}/prior_obj.json', 'w'), indent=1)
