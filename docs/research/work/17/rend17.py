"""Marker-local textured patch rendering (dense point splats from the scan) and masked NCC matching."""
import os, numpy as np, cv2, trimesh
import lib17 as L
_D = {}
def dense_local(n, rad=0.03, dens=30.0):
    """Dense samples (points, gray, normals, marker id) within `rad` of each catalogue marker of object n."""
    if n in _D: return _D[n]
    f = f'{L.ROOT}/work/17/out/dense_{n}.npz'
    if os.path.exists(f):
        z = np.load(f); _D[n] = (z['P'], z['g'], z['N'], z['k']); return _D[n]
    p = f'{L.PUB}/mesh/{n}/{n}.glb'
    if not os.path.exists(p): p = f'{L.PUB}/mesh/{n}/{n}_visual.glb'
    g = list(trimesh.load(p).geometry.values())[0]
    tex = np.asarray(g.visual.material.baseColorTexture.convert('RGB')).astype(np.float32) / 255.
    nsgn = np.sign(np.mean(((g.triangles_center - g.triangles_center.mean(0)) * g.face_normals).sum(1)))
    M = np.array([q['c'] for q in L.CAT[n]]); Ps, gs, Ns, ks = [], [], [], []
    rng = np.random.default_rng(0)
    for k, m in enumerate(M):
        sel = np.flatnonzero(np.linalg.norm(g.triangles_center - m, axis=1) < rad + 0.003)
        a = g.area_faces[sel]; npts = int(a.sum() * 1e6 * dens)
        fi = sel[rng.choice(len(sel), npts, p=a / a.sum())]
        r1, r2 = rng.random(npts), rng.random(npts); s1 = np.sqrt(r1); b = np.stack([1 - s1, s1 * (1 - r2), s1 * r2], 1)
        P = (b[:, :, None] * g.vertices[g.faces[fi]]).sum(1)
        uv = (b[:, :, None] * g.visual.uv[g.faces[fi]]).sum(1); H, W = tex.shape[:2]
        u = np.clip((uv[:, 0] % 1.0) * (W - 1), 0, W - 1); v = np.clip((1 - (uv[:, 1] % 1.0)) * (H - 1), 0, H - 1)
        C = tex[v.round().astype(int), u.round().astype(int)]
        keep = np.linalg.norm(P - m, axis=1) < rad
        Ps.append(P[keep]); gs.append((C[keep] @ [0.299, 0.587, 0.114])); Ns.append(g.face_normals[fi][keep] * nsgn); ks.append(np.full(keep.sum(), k))
    P, gg, N, kk = [np.concatenate(x) for x in (Ps, gs, Ns, ks)]
    np.savez(f, P=P.astype(np.float32), g=gg.astype(np.float32), N=N.astype(np.float32), k=kk.astype(np.int16))
    _D[n] = (P, gg, N, kk); return _D[n]
def render_patch(n, k, Ro, to, Rwc, C, c, zbuf=None, step=None):
    """Render the scan patch around marker k of object n (pose Ro,to) into camera c. Returns (x0,y0,T,Mask) or None."""
    P, gg, N, kk = dense_local(n); m = kk == k
    Pw = P[m] @ Ro.T + to; Nw = N[m] @ Ro.T
    cam_c = C if c == 'a' else C - (Rwc @ (L.T_a_to(c)[:3, :3].T @ L.T_a_to(c)[:3, 3]))
    front = ((Pw - cam_c) * Nw).sum(1) < 0
    Pw, g = Pw[front], gg[m][front]
    if len(Pw) < 100: return None
    uv, z = L.project(Pw, Rwc, C, c)
    K, d, (W, H) = L.cam(c)
    u, v = np.round(uv[:, 0]).astype(int), np.round(uv[:, 1]).astype(int)
    x0, y0, x1, y1 = u.min() - 1, v.min() - 1, u.max() + 2, v.max() + 2
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H or (x1 - x0) * (y1 - y0) > 400 * 400: return None
    o = np.argsort(-z); T = np.zeros((y1 - y0, x1 - x0), np.float32); Z = np.full(T.shape, np.inf, np.float32)
    T[v[o] - y0, u[o] - x0] = g[o]; Z[v[o] - y0, u[o] - x0] = z[o]
    Mk = np.isfinite(Z).astype(np.uint8)
    # fill 1-px holes
    Tf = cv2.dilate(T, np.ones((3, 3), np.uint8)); Mf = cv2.morphologyEx(Mk, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    T = np.where(Mk > 0, T, Tf); Mk = Mf
    if zbuf is not None:  # mask out pixels where another surface (other objects) is in front
        zb, st = zbuf
        zz = cv2.resize(zb[y0 // st:(y1 + st - 1) // st, x0 // st:(x1 + st - 1) // st], (T.shape[1], T.shape[0]), interpolation=cv2.INTER_NEAREST)
        Zf = np.where(np.isfinite(Z), Z, cv2.erode(np.where(np.isfinite(Z), Z, 1e3).astype(np.float32), np.ones((3, 3), np.uint8)))
        Mk = Mk & (Zf <= zz + 0.01).astype(np.uint8)
    return x0, y0, T, Mk
def match(G, x0, y0, T, Mk, win):
    H, W = G.shape; h, w = T.shape
    X0, Y0 = x0 - win, y0 - win
    if X0 < 0 or Y0 < 0 or X0 + w + 2 * win > W or Y0 + h + 2 * win > H or Mk.sum() < 50: return None
    S = G[Y0:Y0 + h + 2 * win, X0:X0 + w + 2 * win]
    R = cv2.matchTemplate(S, T, cv2.TM_CCOEFF_NORMED, mask=Mk)
    R = np.nan_to_num(R, nan=-1, posinf=-1, neginf=-1)
    v, u = np.unravel_index(np.argmax(R), R.shape); sc = R[v, u]
    dx = dy = 0.0
    if 0 < u < R.shape[1] - 1: dx = 0.5 * (R[v, u - 1] - R[v, u + 1]) / (R[v, u - 1] - 2 * sc + R[v, u + 1] - 1e-9)
    if 0 < v < R.shape[0] - 1: dy = 0.5 * (R[v - 1, u] - R[v + 1, u]) / (R[v - 1, u] - 2 * sc + R[v + 1, u] - 1e-9)
    # second-best peak outside a small neighbourhood (ambiguity)
    R2 = R.copy(); R2[max(v - 6, 0):v + 7, max(u - 6, 0):u + 7] = -1
    return dict(dx=u - win + float(np.clip(dx, -1, 1)), dy=v - win + float(np.clip(dy, -1, 1)), score=float(sc), second=float(R2.max()))
