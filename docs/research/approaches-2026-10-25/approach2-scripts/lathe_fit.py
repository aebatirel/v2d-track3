#!/usr/bin/env python
"""L1 lathe rule (RULES.md, frozen 2026-10-25 08:46 UTC). GT-free: reads only OUR library mesh.
Usage: lathe_fit.py NAME MESH OUT_PREFIX
Writes OUT_PREFIX.glb (scoring mesh: lathe body + kept appendage faces), OUT_PREFIX_body.glb (watertight lathe body),
OUT_PREFIX_app.glb (appendage faces), OUT_PREFIX.json (parameters and [M] residuals)."""
import sys, json, math, numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.ndimage import median_filter

NB = 36

def fib_hemi(n):
    i = np.arange(n) + 0.5
    z = 1 - i / n                                   # z in (0,1]
    phi = math.pi * (3 - math.sqrt(5)) * i
    r = np.sqrt(1 - z * z)
    return np.c_[r * np.cos(phi), r * np.sin(phi), z]

def basis(d):
    d = d / np.linalg.norm(d)
    a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(d, a); e1 /= np.linalg.norm(e1)
    return e1, np.cross(d, e1), d

def kasa(xy, its=3):
    w = np.ones(len(xy))
    for _ in range(its):
        A = np.c_[2 * xy, np.ones(len(xy))] * w[:, None]
        x = np.linalg.lstsq(A, (xy ** 2).sum(1) * w, rcond=None)[0]
        c = x[:2]; r = math.sqrt(max(x[2] + c @ c, 1e-12))
        res = np.abs(np.linalg.norm(xy - c, axis=1) - r)
        s = 1.4826 * np.median(res) + 1e-4
        w = 1.0 / np.maximum(1.0, res / (2 * s))
    return c, r, np.linalg.norm(xy - c, axis=1) - r

def score_axis(P, N, d, slab=0.005):
    e1, e2, d = basis(d)
    h = P @ d; X = np.c_[P @ e1, P @ e2]; NX = np.c_[N @ e1, N @ e2]
    ext = h.max() - h.min(); vals, span = [], 0
    for h0 in np.arange(h.min(), h.max(), slab):
        k = (h >= h0) & (h < h0 + slab)
        if k.sum() < 30: continue
        c, r, _ = kasa(X[k], 1)
        v = X[k] - c; nr = (NX[k] * v).sum(1) / np.maximum(np.linalg.norm(v, axis=1), 1e-9)
        o = nr > 0.3
        if o.sum() < 20: continue
        c, r, res = kasa(X[k][o], 3)
        th = np.arctan2(X[k][o][:, 1] - c[1], X[k][o][:, 0] - c[0])
        cov = len(np.unique(np.minimum(((th + np.pi) / (2 * np.pi) * NB).astype(int), NB - 1))) / NB
        if cov < 0.5: continue
        vals.append(np.median(np.abs(res)) / r); span += slab
    if not vals or span < 0.3 * ext:
        return np.inf, 0.0
    return float(np.median(vals)), span / ext

def refine_axis(P, N, c0, d, slab=0.004, iters=4):
    d0 = d.copy(); c_start = c0.copy()
    for _ in range(iters):
        e1, e2, d = basis(d)
        h = (P - c0) @ d; X = np.c_[(P - c0) @ e1, (P - c0) @ e2]; NX = np.c_[N @ e1, N @ e2]
        cents, ws = [], []
        for h0 in np.arange(h.min(), h.max(), slab):
            k = (h >= h0) & (h < h0 + slab)
            if k.sum() < 30: continue
            c, r, _ = kasa(X[k], 1)
            v = X[k] - c; nr = (NX[k] * v).sum(1) / np.maximum(np.linalg.norm(v, axis=1), 1e-9)
            o = nr > 0.3
            if o.sum() < 20: continue
            c, r, res = kasa(X[k][o], 3)
            th = np.arctan2(X[k][o][:, 1] - c[1], X[k][o][:, 0] - c[0])
            cov = len(np.unique(np.minimum(((th + np.pi) / (2 * np.pi) * NB).astype(int), NB - 1))) / NB
            if cov < 0.5 or np.median(np.abs(res)) > 0.08 * r: continue
            cents.append(c0 + c[0] * e1 + c[1] * e2 + (h0 + slab / 2) * d); ws.append(cov)
        if len(cents) < 4: break
        C = np.array(cents); W = np.array(ws); mu = (C * W[:, None]).sum(0) / W.sum()
        Vt = np.linalg.svd((C - mu) * np.sqrt(W)[:, None], full_matrices=False)[2]
        dn = Vt[0] * np.sign(Vt[0] @ d); c0, d = mu, dn / np.linalg.norm(dn)
    if math.degrees(math.acos(min(1, abs(d @ d0)))) > 15:
        return c_start, d0, False
    return c0, d, True

def disc_centre(P, N, d):
    """centre of the axis for a disc (refine rejected): Kasa fit of outward points in the mid slab"""
    e1, e2, d = basis(d); c = P.mean(0)
    X = np.c_[(P - c) @ e1, (P - c) @ e2]
    cc, r, _ = kasa(X, 3)
    return c + cc[0] * e1 + cc[1] * e2

def main(name, path, outp):
    m = trimesh.load(path, force='mesh')
    P, fi = trimesh.sample.sample_surface(m, 60000, seed=0); P = np.asarray(P); N = np.asarray(m.face_normals[fi])
    rng = np.random.default_rng(0); sub = rng.choice(len(P), 15000, replace=False)
    cen = P.mean(0); ev, V = np.linalg.eigh(np.cov((P - cen).T))
    disc = ev[0] < 0.1 * ev[1]
    cands = [V[:, k] for k in range(3)] + list(fib_hemi(400))
    best = (np.inf, None, 0)
    for d in cands:
        s, sp = score_axis(P[sub], N[sub], np.asarray(d))
        if s < best[0]: best = (s, np.asarray(d), sp)
    info = dict(name=name, src=path, disc=bool(disc), pca_eig_cm2=[round(float(x) * 1e4, 2) for x in ev],
                axis_score=round(best[0], 4), axis_span=round(best[2], 2))
    if not np.isfinite(best[0]) or best[0] > 0.05:
        info['verdict'] = 'not a lathe (gate B)'
        json.dump(info, open(outp + '.json', 'w'), indent=1); print(json.dumps(info)); return
    c0, d, ok = refine_axis(P, N, cen, best[1])
    if not ok:
        c0 = disc_centre(P, N, d)
    info['refined'] = bool(ok)
    e1, e2, d = basis(d)
    Q = P - c0; h = Q @ d; x = Q @ e1; y = Q @ e2; r = np.hypot(x, y); th = np.arctan2(y, x)
    nr = (N @ e1) * x / np.maximum(r, 1e-9) + (N @ e2) * y / np.maximum(r, 1e-9); nh = N @ d
    dh = 0.002; h0 = h.min(); hb = np.floor((h - h0) / dh).astype(int); nb = hb.max() + 1
    tb = np.minimum(((th + np.pi) / (2 * np.pi) * NB).astype(int), NB - 1)
    Ro = np.full((nb, NB), -1.0); Ri = np.full((nb, NB), -1.0)
    o = nr > 0.3; i_ = nr < -0.3
    np.maximum.at(Ro, (hb[o], tb[o]), r[o]); np.maximum.at(Ri, (hb[i_], tb[i_]), r[i_])
    Ro[Ro < 0] = np.nan; Ri[Ri < 0] = np.nan; Ri[~(Ri < Ro - 0.001)] = np.nan
    cov = np.mean(np.isfinite(Ro), 1); covi = np.mean(np.isfinite(Ri), 1)
    with np.errstate(all='ignore'):
        ro = np.nanmedian(Ro, 1)
    keep = cov >= 0.25
    idx = np.where(keep)[0]
    ro_s = np.full(nb, np.nan); ro_s[idx] = median_filter(ro[idx], size=5, mode='nearest')
    rmax = np.nanmax(ro_s)
    good = keep & (ro_s >= 0.5 * rmax)
    # longest contiguous run of good bins
    best_run, cur = (0, -1), None
    for k in range(nb):
        if good[k]:
            cur = k if cur is None else cur
            if k - cur > best_run[1] - best_run[0]: best_run = (cur, k)
        else:
            cur = None
    b0, b1 = best_run
    hc = h0 + (np.arange(nb) + 0.5) * dh
    body = np.arange(b0, b1 + 1)
    # caps
    def capped(end_bin, sign):
    	pass
    def cap_frac(hend, rend, inward):
        k = (np.abs(nh) > 0.7) & (r < 0.8 * rend) & (((h - hend) * inward) >= -0.002) & (((h - hend) * inward) <= 0.015)
        g = 0.004; n = int(np.ceil(0.8 * rend / g))
        gx = np.floor(x[k] / g).astype(int); gy = np.floor(y[k] / g).astype(int)
        occ = set(zip(gx.tolist(), gy.tolist()))
        cells = [(a, b) for a in range(-n - 1, n + 1) for b in range(-n - 1, n + 1) if ((a + .5) * g) ** 2 + ((b + .5) * g) ** 2 < (0.8 * rend) ** 2]
        return sum(c in occ for c in cells) / max(len(cells), 1)
    hlo, hhi = hc[b0] - dh / 2, hc[b1] + dh / 2
    rlo = float(np.nanmean(ro_s[b0:b0 + 5])); rhi = float(np.nanmean(ro_s[max(b1 - 4, b0):b1 + 1]))
    cf_lo, cf_hi = cap_frac(hlo, rlo, +1), cap_frac(hhi, rhi, -1)
    cap_lo, cap_hi = cf_lo >= 0.5, cf_hi >= 0.5
    if cap_lo != cap_hi:
        base = 'lo' if cap_lo else 'hi'
    else:
        base = 'lo' if rlo < rhi else 'hi'
    mouth_capped = cap_hi if base == 'lo' else cap_lo
    info.update(axis_c_cm=[round(float(v) * 100, 3) for v in c0], axis_d=[round(float(v), 4) for v in d],
                body_h_cm=[round(hlo * 100, 2), round(hhi * 100, 2)], r_end_cm=[round(rlo * 100, 2), round(rhi * 100, 2)],
                cap_frac=[round(cf_lo, 2), round(cf_hi, 2)], base=base, rmax_cm=round(rmax * 100, 2),
                bins_kept=int(keep.sum()), bins_body=int(len(body)))
    hollow = (not mouth_capped) and (not disc)
    prof_h = hc[body]; prof_r = ro_s[body]
    # fill any nan inside body (should not happen) by interpolation
    okk = np.isfinite(prof_r); prof_r = np.interp(prof_h, prof_h[okk], prof_r[okk])
    if base == 'hi':                                   # orient so that the base is at index 0
        prof_h = prof_h[::-1]; prof_r = prof_r[::-1]; hb_plane = hhi; hm_plane = hlo; sgn = -1
    else:
        hb_plane = hlo; hm_plane = hhi; sgn = 1
    t = None
    if hollow:
        mouth_bins = body[np.abs(hc[body] - hm_plane) <= 0.010]
        vals = []
        for k in mouth_bins:
            if covi[k] >= 0.5:
                dd = Ro[k] - Ri[k]; dd = dd[np.isfinite(dd)]
                if len(dd): vals.append(np.median(dd))
        t_raw = float(np.median(vals)) if vals else float('nan')
        t = float(np.clip(t_raw if np.isfinite(t_raw) else 0.004, 0.002, 0.008))
        info.update(wall_t_raw_mm=round(t_raw * 1e3, 2) if np.isfinite(t_raw) else None, wall_t_mm=round(t * 1e3, 2), mouth_bins_used=len(vals))
    info['hollow'] = bool(hollow)
    # profile loop (r, h) in axis coordinates; base at prof index 0
    loop = [(0.0, hb_plane), (prof_r[0], hb_plane)] + list(zip(prof_r, prof_h)) + [(prof_r[-1], hm_plane)]
    if hollow:
        hf = hb_plane + sgn * t
        inner = [(max(rr - t, 0.001), hh) for rr, hh in zip(prof_r, prof_h) if sgn * (hh - hf) > 0]
        loop += [(max(prof_r[-1] - t, 0.001), hm_plane)] + inner[::-1] + [(max(inner[0][0], 0.001) if inner else 0.001, hf), (0.0, hf)]
    else:
        loop += [(0.0, hm_plane)]
    # dedupe consecutive
    L = [loop[0]]
    for p in loop[1:]:
        if abs(p[0] - L[-1][0]) > 1e-6 or abs(p[1] - L[-1][1]) > 1e-6: L.append(p)
    S = 64; ang = np.linspace(0, 2 * np.pi, S, endpoint=False)
    verts, faces, ring_idx = [], [], []
    for (rr, hh) in L:
        if rr <= 1e-6:
            ring_idx.append([len(verts)] * S); verts.append(c0 + hh * d)
        else:
            ids = list(range(len(verts), len(verts) + S)); ring_idx.append(ids)
            for a in ang: verts.append(c0 + hh * d + rr * (math.cos(a) * e1 + math.sin(a) * e2))
    for k in range(len(L) - 1):
        A, B = ring_idx[k], ring_idx[k + 1]
        for s in range(S):
            a0, a1, b0_, b1_ = A[s], A[(s + 1) % S], B[s], B[(s + 1) % S]
            if a0 != a1: faces.append([a0, a1, b1_] if b0_ == b1_ else [a0, a1, b0_])
            if b0_ != b1_: faces.append([a1, b1_, b0_])
    body_m = trimesh.Trimesh(np.array(verts), np.array(faces), process=True)
    body_m.fix_normals()
    info.update(body_faces=int(len(body_m.faces)), body_watertight=bool(body_m.is_watertight), body_volume_cm3=round(float(body_m.volume) * 1e6, 1))
    # appendages: faces of our mesh > 5 mm outside the lathe body
    fc = m.triangles_center - c0; fh = fc @ d; fr = np.hypot(fc @ e1, fc @ e2)
    order = np.argsort(prof_h); r_at = np.interp(fh, prof_h[order], prof_r[order])
    hmin, hmax = min(hb_plane, hm_plane), max(hb_plane, hm_plane)
    out_side = (fr > r_at + 0.005) | (fh < hmin - 0.005) | (fh > hmax + 0.005)
    app = m.submesh([np.where(out_side)[0]], append=True) if out_side.any() else None
    info['appendage_faces'] = int(out_side.sum()); info['appendage_area_cm2'] = round(float(app.area) * 1e4, 1) if app is not None else 0.0
    score_m = trimesh.util.concatenate([body_m, app]) if app is not None else body_m
    body_m.export(outp + '_body.glb'); score_m.export(outp + '.glb')
    if app is not None: app.export(outp + '_app.glb')
    # [M] residuals ours <-> lathe scoring mesh
    A = m.sample(20000); B = score_m.sample(20000)
    dA = cKDTree(B).query(A)[0]; dB = cKDTree(A).query(B)[0]
    info.update(M_sym_mean_mm=round(0.5 * (dA.mean() + dB.mean()) * 1e3, 2), M_ours_to_lathe_med_mm=round(float(np.median(dA)) * 1e3, 2),
                M_ours_to_lathe_p90_mm=round(float(np.percentile(dA, 90)) * 1e3, 2), M_lathe_to_ours_med_mm=round(float(np.median(dB)) * 1e3, 2),
                M_lathe_to_ours_p90_mm=round(float(np.percentile(dB, 90)) * 1e3, 2))
    # circularity residual of OUR mesh about the fitted axis (body bins)
    with np.errstate(all='ignore'):
        circ = np.nanmedian(np.abs(Ro[body] - ro[body][:, None]), 1)
    info['M_circ_mad_mm'] = round(float(np.nanmedian(circ)) * 1e3, 2)
    np.savez(outp + '_profile.npz', hc=hc, Ro=Ro, Ri=Ri, cov=cov, covi=covi, ro_s=ro_s, body=body, c0=c0, d=d, e1=e1, e2=e2,
             prof_h=prof_h, prof_r=prof_r, t=np.nan if t is None else t, hb_plane=hb_plane, hm_plane=hm_plane)
    json.dump(info, open(outp + '.json', 'w'), indent=1)
    print(json.dumps(info))

if __name__ == '__main__':
    main(*sys.argv[1:4])
