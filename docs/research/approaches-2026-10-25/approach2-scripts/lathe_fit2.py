#!/usr/bin/env python
"""L1 lathe rule, revision v2 (RULES.md). GT-free: reads only OUR library mesh. Same outputs as lathe_fit.py."""
import sys, os, json, math, numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.ndimage import median_filter
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from lathe_fit import fib_hemi, basis, kasa, score_axis, refine_axis, disc_centre, NB

def line_complex_axis(P, N, its=5):
    """Pottmann-Randrup: find the line (dir a, moment m) that all normal lines intersect: n.m + (p x n).a = 0."""
    mu = P.mean(0); Q = P - mu
    M = np.c_[N, np.cross(Q, N)]
    w = np.ones(len(M))
    for _ in range(its):
        G = (M * w[:, None]).T @ M
        A, B, C = G[:3, :3], G[:3, 3:], G[3:, 3:]
        S = C - B.T @ np.linalg.solve(A + 1e-12 * np.eye(3), B)
        ev, V = np.linalg.eigh(S); a = V[:, 0]
        m = -np.linalg.solve(A + 1e-12 * np.eye(3), B @ a)
        res = np.abs(M @ np.r_[m, a])
        s = 1.4826 * np.median(res) + 1e-9
        w = 1.0 / np.maximum(1.0, res / (2 * s))
    q = np.cross(a, m) / (a @ a)
    return mu + q, a / np.linalg.norm(a)

def profile(P, N, c0, d, dh=0.002):
    e1, e2, d = basis(d)
    Q = P - c0; h = Q @ d; x = Q @ e1; y = Q @ e2; r = np.hypot(x, y); th = np.arctan2(y, x)
    nr = (N @ e1) * x / np.maximum(r, 1e-9) + (N @ e2) * y / np.maximum(r, 1e-9); nh = N @ d
    h0 = h.min(); hb = np.floor((h - h0) / dh).astype(int); nb = hb.max() + 1
    tb = np.minimum(((th + np.pi) / (2 * np.pi) * NB).astype(int), NB - 1)
    Ro = np.full((nb, NB), -1.0); Ri = np.full((nb, NB), -1.0)
    o = nr > 0.3; i_ = nr < -0.3
    np.maximum.at(Ro, (hb[o], tb[o]), r[o]); np.maximum.at(Ri, (hb[i_], tb[i_]), r[i_])
    Ro[Ro < 0] = np.nan; Ri[Ri < 0] = np.nan; Ri[~(Ri < Ro - 0.001)] = np.nan
    cov = np.mean(np.isfinite(Ro), 1); covi = np.mean(np.isfinite(Ri), 1)
    with np.errstate(all='ignore'):
        import warnings; warnings.simplefilter('ignore')
        ro = np.nanmedian(Ro, 1)
    keep = cov >= 0.25; idx = np.where(keep)[0]
    ro_s = np.full(nb, np.nan)
    if len(idx): ro_s[idx] = median_filter(ro[idx], size=5, mode='nearest')
    rmax = np.nanmax(ro_s) if len(idx) else np.nan
    good = keep & (ro_s >= 0.5 * rmax)
    best_run, cur = (0, -1), None
    for k in range(nb):
        if good[k]:
            cur = k if cur is None else cur
            if k - cur > best_run[1] - best_run[0]: best_run = (cur, k)
        else:
            cur = None
    b0, b1 = best_run; body = np.arange(b0, b1 + 1)
    hc = h0 + (np.arange(nb) + 0.5) * dh
    with np.errstate(all='ignore'):
        circ = np.nanmedian(np.abs(Ro[body] - ro[body][:, None]), 1) if len(body) else np.array([np.nan])
    return dict(e1=e1, e2=e2, d=d, h=h, r=r, x=x, y=y, nh=nh, hc=hc, Ro=Ro, Ri=Ri, cov=cov, covi=covi, ro=ro, ro_s=ro_s,
                rmax=rmax, body=body, b0=b0, b1=b1, dh=dh, circ_mad=float(np.nanmedian(circ)) if len(body) else np.inf)

def main(name, path, outp):
    m = trimesh.load(path, force='mesh')
    P, fi = trimesh.sample.sample_surface(m, 60000, seed=0); P = np.asarray(P); N = np.asarray(m.face_normals[fi])
    rng = np.random.default_rng(0); sub = rng.choice(len(P), 15000, replace=False)
    cen = P.mean(0); ev, V = np.linalg.eigh(np.cov((P - cen).T)); disc = ev[0] < 0.1 * ev[1]
    best = (np.inf, None)
    for dvec in fib_hemi(400):
        s, sp = score_axis(P[sub], N[sub], np.asarray(dvec))
        if s < best[0]: best = (s, np.asarray(dvec))
    lc_c, lc_d = line_complex_axis(P[sub], N[sub])
    starts = [('pca0', cen, V[:, 0]), ('pca1', cen, V[:, 1]), ('pca2', cen, V[:, 2]), ('fib', cen, best[1]), ('linecomplex', lc_c, lc_d)]
    cands = []
    for lab, c_s, d_s in starts:
        if d_s is None: continue
        c1, d1, ok = refine_axis(P, N, c_s, d_s)
        if not ok:
            c1 = disc_centre(P, N, d1) if lab != 'linecomplex' else c_s
        pr = profile(P, N, c1, d1)
        sc = pr['circ_mad'] / pr['rmax'] if np.isfinite(pr['rmax']) and len(pr['body']) > 5 else np.inf
        slab, span = score_axis(P[sub], N[sub], d1)
        cands.append(dict(lab=lab, c=c1, d=pr['d'], ok=ok, pr=pr, sel=sc, slab=slab, span=span))
    cands.sort(key=lambda z: z['sel'])
    ch = cands[0]; pr = ch['pr']
    info = dict(name=name, src=path, rule='v2', disc=bool(disc), pca_eig_cm2=[round(float(x) * 1e4, 2) for x in ev],
                candidates=[dict(lab=z['lab'], refined=z['ok'], sel=round(z['sel'], 4), circ_mad_mm=round(z['pr']['circ_mad'] * 1e3, 2),
                                 slab_score=round(z['slab'], 4), d=[round(float(v), 3) for v in z['d']]) for z in cands],
                chosen=ch['lab'], axis_score=round(ch['slab'], 4), M_circ_mad_mm=round(pr['circ_mad'] * 1e3, 2))
    if not (ch['slab'] <= 0.05) or pr['circ_mad'] > 0.003:
        info['verdict'] = 'not a lathe (gate B/B2)'
        json.dump(info, open(outp + '.json', 'w'), indent=1); print(json.dumps({k: v for k, v in info.items() if k != 'src'})); return
    c0 = ch['c']; e1, e2, d = pr['e1'], pr['e2'], pr['d']
    h, r, x, y, nh = pr['h'], pr['r'], pr['x'], pr['y'], pr['nh']
    hc, Ro, Ri, covi, ro_s, body, b0, b1, dh, rmax = pr['hc'], pr['Ro'], pr['Ri'], pr['covi'], pr['ro_s'], pr['body'], pr['b0'], pr['b1'], pr['dh'], pr['rmax']
    def cap_frac(hend, rend, inward):
        k = (np.abs(nh) > 0.7) & (r < 0.8 * rend) & (((h - hend) * inward) >= -0.002) & (((h - hend) * inward) <= 0.015)
        g = 0.004; n = int(np.ceil(0.8 * rend / g))
        occ = set(zip(np.floor(x[k] / g).astype(int).tolist(), np.floor(y[k] / g).astype(int).tolist()))
        cells = [(a, b) for a in range(-n - 1, n + 1) for b in range(-n - 1, n + 1) if ((a + .5) * g) ** 2 + ((b + .5) * g) ** 2 < (0.8 * rend) ** 2]
        return sum(c in occ for c in cells) / max(len(cells), 1)
    hlo, hhi = hc[b0] - dh / 2, hc[b1] + dh / 2
    rlo = float(np.nanmean(ro_s[b0:b0 + 5])); rhi = float(np.nanmean(ro_s[max(b1 - 4, b0):b1 + 1]))
    cf_lo, cf_hi = cap_frac(hlo, rlo, +1), cap_frac(hhi, rhi, -1)
    cap_lo, cap_hi = cf_lo >= 0.5, cf_hi >= 0.5
    base = ('lo' if cap_lo else 'hi') if cap_lo != cap_hi else ('lo' if rlo < rhi else 'hi')
    mouth_capped = cap_hi if base == 'lo' else cap_lo
    info.update(axis_c_cm=[round(float(v) * 100, 3) for v in c0], axis_d=[round(float(v), 4) for v in d],
                body_h_cm=[round(hlo * 100, 2), round(hhi * 100, 2)], r_end_cm=[round(rlo * 100, 2), round(rhi * 100, 2)],
                cap_frac=[round(cf_lo, 2), round(cf_hi, 2)], base=base, rmax_cm=round(rmax * 100, 2), bins_body=int(len(body)))
    hollow = (not mouth_capped) and (not disc) and os.environ.get("LATHE_SOLID", "0") != "1"
    prof_h = hc[body]; prof_r = ro_s[body]; okk = np.isfinite(prof_r); prof_r = np.interp(prof_h, prof_h[okk], prof_r[okk])
    if base == 'hi':
        prof_h = prof_h[::-1]; prof_r = prof_r[::-1]; hb_plane, hm_plane, sgn = hhi, hlo, -1
    else:
        hb_plane, hm_plane, sgn = hlo, hhi, 1
    t = None
    if hollow:
        def tvals(win, cmin):
            v = []
            for k in body[np.abs(hc[body] - hm_plane) <= win]:
                if covi[k] >= cmin:
                    dd = Ro[k] - Ri[k]; dd = dd[np.isfinite(dd)]
                    if len(dd): v.append(np.median(dd))
            return v
        vals = tvals(0.010, 0.5); src = '10mm/0.5'
        if not vals: vals = tvals(0.020, 0.25); src = '20mm/0.25'
        t_raw = float(np.median(vals)) if vals else float('nan')
        if not vals: src = 'default'
        t = float(np.clip(t_raw, 0.002, 0.008)) if np.isfinite(t_raw) else 0.004
        info.update(wall_t_raw_mm=round(t_raw * 1e3, 2) if np.isfinite(t_raw) else None, wall_t_mm=round(t * 1e3, 2), wall_t_src=src, wall_t_bins=len(vals))
    info['hollow'] = bool(hollow)
    loop = [(0.0, hb_plane), (prof_r[0], hb_plane)] + list(zip(prof_r, prof_h)) + [(prof_r[-1], hm_plane)]
    if hollow:
        hf = hb_plane + sgn * t
        inner = [(max(rr - t, 0.001), hh) for rr, hh in zip(prof_r, prof_h) if sgn * (hh - hf) > 0]
        loop += [(max(prof_r[-1] - t, 0.001), hm_plane)] + inner[::-1] + [(inner[0][0] if inner else 0.001, hf), (0.0, hf)]
    else:
        loop += [(0.0, hm_plane)]
    L = [loop[0]]
    for p in loop[1:]:
        if abs(p[0] - L[-1][0]) > 1e-6 or abs(p[1] - L[-1][1]) > 1e-6: L.append(p)
    S = 64; ang = np.linspace(0, 2 * np.pi, S, endpoint=False)
    verts, faces, ring = [], [], []
    for (rr, hh) in L:
        if rr <= 1e-6:
            ring.append([len(verts)] * S); verts.append(c0 + hh * d)
        else:
            ids = list(range(len(verts), len(verts) + S)); ring.append(ids)
            for a in ang: verts.append(c0 + hh * d + rr * (math.cos(a) * e1 + math.sin(a) * e2))
    for k in range(len(L) - 1):
        A, B = ring[k], ring[k + 1]
        for s in range(S):
            a0, a1, c0_, c1_ = A[s], A[(s + 1) % S], B[s], B[(s + 1) % S]
            if a0 != a1: faces.append([a0, a1, c1_] if c0_ == c1_ else [a0, a1, c0_])
            if c0_ != c1_: faces.append([a1, c1_, c0_])
    body_m = trimesh.Trimesh(np.array(verts), np.array(faces), process=True); body_m.fix_normals()
    info.update(body_faces=int(len(body_m.faces)), body_watertight=bool(body_m.is_watertight), body_volume_cm3=round(float(body_m.volume) * 1e6, 1))
    fc = m.triangles_center - c0; fh = fc @ d; fr = np.hypot(fc @ e1, fc @ e2)
    o = np.argsort(prof_h); r_at = np.interp(fh, prof_h[o], prof_r[o])
    hmin, hmax = min(hb_plane, hm_plane), max(hb_plane, hm_plane)
    out_side = (fr > r_at + 0.005) | (fh < hmin - 0.005) | (fh > hmax + 0.005)
    app = m.submesh([np.where(out_side)[0]], append=True) if out_side.any() else None
    info['appendage_faces'] = int(out_side.sum()); info['appendage_area_cm2'] = round(float(app.area) * 1e4, 1) if app is not None else 0.0
    score_m = trimesh.util.concatenate([body_m, app]) if app is not None else body_m
    body_m.export(outp + '_body.glb'); score_m.export(outp + '.glb')
    if app is not None: app.export(outp + '_app.glb')
    A_ = m.sample(20000); B_ = score_m.sample(20000)
    dA = cKDTree(B_).query(A_)[0]; dB = cKDTree(A_).query(B_)[0]
    info.update(M_sym_mean_mm=round(0.5 * (dA.mean() + dB.mean()) * 1e3, 2), M_ours_to_lathe_med_mm=round(float(np.median(dA)) * 1e3, 2),
                M_ours_to_lathe_p90_mm=round(float(np.percentile(dA, 90)) * 1e3, 2), M_lathe_to_ours_med_mm=round(float(np.median(dB)) * 1e3, 2),
                M_lathe_to_ours_p90_mm=round(float(np.percentile(dB, 90)) * 1e3, 2))
    np.savez(outp + '_profile.npz', hc=hc, Ro=Ro, Ri=Ri, covi=covi, ro_s=ro_s, body=body, c0=c0, d=d, e1=e1, e2=e2,
             prof_h=prof_h, prof_r=prof_r, t=np.nan if t is None else t, hb_plane=hb_plane, hm_plane=hm_plane)
    json.dump(info, open(outp + '.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in info.items() if k not in ('src', 'candidates')}))

if __name__ == '__main__':
    main(*sys.argv[1:4])
