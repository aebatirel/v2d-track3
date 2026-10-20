"""Locate Vicon marker bases in the textured public scans (dark, unsaturated texels), cluster them,
and test how much the markers drive the surface-covariance frame (rule R1 of note 07)."""
from c11 import *
import trimesh, os, json
from scipy.cluster.hierarchy import fcluster, linkage

def load_tex(name):
    p = f"{PUB}/mesh/{name}/{name}.glb"
    if not os.path.exists(p): p = p.replace('.glb', '_visual.glb')
    s = trimesh.load(p, force='scene'); g = list(s.geometry.values())[0]
    return g

def face_colours(g):
    uv = g.visual.uv; img = np.asarray(g.visual.material.baseColorTexture.convert('RGB'))
    H, W = img.shape[:2]
    fuv = uv[g.faces].mean(1)
    px = np.clip((fuv[:, 0] % 1) * (W - 1), 0, W - 1).astype(int); py = np.clip((1 - fuv[:, 1] % 1) * (H - 1), 0, H - 1).astype(int)
    return img[py, px].astype(float)

def surf_frame(V, F, mask=None):
    tri = V[F] if mask is None else V[F[mask]]
    a = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    c = (a[:, None] * tri.mean(1)).sum(0) / a.sum()
    # exact area-weighted second moment of triangles
    X = tri - c
    C = np.zeros((3, 3))
    for i in range(3):
        C += (a[:, None, None] * np.einsum('fi,fj->fij', X[:, i], X[:, i])).sum(0) / 12
    S = X.sum(1); C += (a[:, None, None] * np.einsum('fi,fj->fij', S, S)).sum(0) / 12
    C /= a.sum()
    w, E = np.linalg.eigh(C)
    # third moment along each axis (sampled approx via vertices of triangles + centroid, area-weighted)
    P = np.concatenate([tri.mean(1), tri[:, 0], tri[:, 1], tri[:, 2]]) - c
    wt = np.concatenate([a * 0.75, a / 12, a / 12, a / 12])
    proj = P @ E
    sk = (wt[:, None] * proj ** 3).sum(0) / wt.sum() / (w ** 1.5)
    return c, w, E, sk, a.sum()

out = {}
for nm in ["beige_cup", "blue_cup", "white_pot_lid", "white_pot", "plastic_dish_rack", "water_pitcher",
           "mini_dust_pan", "mini_sweeper", "wooden_piece_1", "wooden_piece_2"]:
    g = load_tex(nm); V, F = np.asarray(g.vertices, float), np.asarray(g.faces)
    col = face_colours(g)
    mx, mn = col.max(1), col.min(1)
    dark = (mx < 55) & (mx - mn < 30)
    fc = V[F].mean(1)
    ctr = []
    if dark.sum() > 3:
        Z = linkage(fc[dark], 'single'); lab = fcluster(Z, 0.008, 'distance')
        A = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
        for l in np.unique(lab):
            m = lab == l; area = A[dark][m].sum()
            if 3e-5 < area < 6e-4:  # 0.3-6 cm^2 (one marker base)
                ctr.append((fc[dark][m].mean(0), area))
    c0, w0, E0, sk0, A0 = surf_frame(V, F)
    # remove faces within 13 mm of each marker-base centroid (base + sphere)
    keep = np.ones(len(F), bool)
    for p_, _ in ctr:
        keep &= np.linalg.norm(fc - p_, axis=1) > 0.013
    c1, w1, E1, sk1, A1 = surf_frame(V, F, keep)
    ang = [np.degrees(np.arccos(min(1, abs(E0[:, k] @ E1[:, k])))) for k in range(3)]
    sgn = [int(np.sign(E0[:, k] @ E1[:, k])) for k in range(3)]
    print(f"\n{nm}: {len(ctr)} dark clusters (marker bases) ; removed area {100*(1-A1/A0):.1f}% ; centroid shift {np.linalg.norm(c1-c0)*1000:.1f} mm")
    for p_, a_ in ctr:
        print(f"   base at {np.round(p_*1000,0)} mm, area {a_*1e4:.2f} cm2")
    print(f"   std mm with {np.round(np.sqrt(w0)*1000,1)} without {np.round(np.sqrt(w1)*1000,1)}")
    print(f"   axis change deg x/y/z {np.round(ang,1)} ; skew with {np.round(sk0,3)} without(in same-sign axes) {np.round(sk1*sgn,3)}")
    out[nm] = dict(n=len(ctr), bases=[(p_.tolist(), a_) for p_, a_ in ctr], ang=ang, sk0=sk0.tolist(), sk1=(sk1 * sgn).tolist())
json.dump(out, open('s4_markers.json', 'w'), indent=1)
