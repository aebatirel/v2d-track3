"""C2/P GT-free diagnosis of the pitcher's C0b observed points (our stereo along our own track; no scan, mocap,
parquet pose or library mesh is read).

Per episode (and for the merged ep21+22 points) it reports [M]:
  - coverage: points, frames, the camera directions in the object frame (elevation / azimuth spread about the fitted
    axis), how many 24-sector cells of each height bin were seen (which episode sees more);
  - axis: lathe_obs.fit_axis (TIE 1.0, as C0b) on the same 60,000-point subsample lathe_obs uses; rotational
    consistency (mm); angle between the episodes' axes;
  - profile: per 3 mm height bin, median outer radius over sectors and its harmonic content
    r(theta) = r0 + a1 cos + b1 sin + a2 cos 2theta + b2 sin 2theta (|a2,b2| = ovality, |a1,b1| = axis offset), fitted
    on the sector medians of the OUTER-viewed points;
  - appendages: points more than 3 sigma (sigma = gmg A.2, from c0b_prep.py sigma) outside the median outer
    profile, grouped by 6 mm voxel connectivity; per group: points, angular span, height span, radial reach
    (handle and spout);
  - observed rest: the table normal in the object frame. World frame = our track's world (world_T_cam); the up
    vector is the normal of the frame-0 table plane fitted to OUR depth by recon_mesh.table_plane, if the depth is
    given; otherwise only the object's motion is reported.
Usage: diag_pitcher.py OUT.json LABEL=OBS.npz[:SIGMA.json][:POSES.npz] ...
"""
import json, os, sys
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))      # docs/research/mesh-2026-10-26
sys.path.insert(0, os.path.join(MR, 'scripts'))
import lathe_obs as L  # noqa: E402

L.TIE = 1.0


def load(spec):
    lab, rest = spec.split('=', 1)
    parts = rest.split(':')
    pts, cam = [], []
    for f in parts[0].split(','):
        z = np.load(f)
        pts.append(z['pts']); cam.append(z['cam'])
    sig = float(np.median([json.load(open(s))['sigma_m'] for s in parts[1].split(',')])) if len(parts) > 1 and parts[1] else None
    return lab, np.concatenate(pts).astype(np.float64), np.concatenate(cam).astype(np.float64), sig


def harmonics(th, r):
    A = np.stack([np.ones_like(th), np.cos(th), np.sin(th), np.cos(2 * th), np.sin(2 * th)], 1)
    c, *_ = np.linalg.lstsq(A, r, rcond=None)
    return c


def analyse(lab, P0, C0, sig):
    # the same preprocessing as lathe_obs: 1.5 mm voxel downsample (first point), 60k subsample for the axis
    key = np.floor(P0 / 0.0015).astype(np.int64)
    _, first = np.unique(key, axis=0, return_index=True)
    P, C = P0[first], C0[first]
    sub = np.random.default_rng(0).choice(len(P), min(60000, len(P)), replace=False)
    cost, c, d, k = L.fit_axis(P[sub], C[sub])
    h, r, th, (e1, e2, d) = L.cyl(P, c, d)
    v = C - P; v /= np.linalg.norm(v, axis=1, keepdims=True)
    radial = np.stack([np.cos(th), np.sin(th)], 1)
    vr = (v @ e1) * radial[:, 0] + (v @ e2) * radial[:, 1]
    outer, inner = vr > 0.3, vr < -0.3
    # camera directions relative to the axis (elevation above the plane normal to the axis; azimuth)
    vc = C0[np.random.default_rng(0).choice(len(C0), min(20000, len(C0)), replace=False)] - c
    el = np.degrees(np.arcsin(np.clip((vc @ d) / np.linalg.norm(vc, axis=1), -1, 1)))
    az = np.degrees(np.arctan2(vc @ e2, vc @ e1))
    # outer profile per height bin and sector
    S, h0 = L.sector_stat(h, r, th, outer, q=50, min_pts=8)
    nsec = np.isfinite(S).sum(1)
    hc = h0 + (np.arange(S.shape[0]) + 0.5) * L.DH
    rows = []
    secc = (np.arange(L.NSEC) + 0.5) / L.NSEC * 2 * np.pi - np.pi
    for i in range(S.shape[0]):
        ok = np.isfinite(S[i])
        row = dict(h_mm=round(hc[i] * 1e3, 1), nsec=int(ok.sum()))
        if ok.sum() >= 6:
            row['r_med_mm'] = round(float(np.median(S[i][ok])) * 1e3, 1)
            row['r_min_mm'] = round(float(np.min(S[i][ok])) * 1e3, 1)
            row['r_max_mm'] = round(float(np.max(S[i][ok])) * 1e3, 1)
            if ok.sum() >= 8:
                hm = harmonics(secc[ok], S[i][ok])
                row['offset_mm'] = round(float(np.hypot(hm[1], hm[2])) * 1e3, 1)
                row['oval_mm'] = round(float(np.hypot(hm[3], hm[4])) * 1e3, 1)
        rows.append(row)
    # inner-wall coverage (two-wall bins as lathe_obs counts them)
    Sin, _ = L.sector_stat(h, r, th, inner, q=50, min_pts=8)
    nin = np.isfinite(Sin).sum(1)
    r_out = np.where(nsec >= 6, np.nanmedian(np.where(np.isfinite(S), S, np.nan), 1), np.nan)
    r_in = np.where(nin >= 6, np.nanmedian(np.where(np.isfinite(Sin), Sin, np.nan), 1), np.nan)
    both = np.isfinite(r_out) & np.isfinite(r_in) & (r_in < r_out)
    t_meas = float(np.median((r_out - r_in)[both])) * 1e3 if both.sum() >= 3 else None
    # appendages: > 3 sigma (or 4 mm if no sigma) outside the filled outer profile
    app_d = 3 * sig if sig else 0.004
    vo = np.isfinite(r_out)
    ro = L.smooth_fill(r_out, vo)
    body = r < np.nanmax(r_out) + 0.005
    hlo, hhi = np.percentile(h[body], [0.5, 99.5])
    rprof = np.interp(h, hc, ro)
    out = (r > rprof + app_d) | (h > hhi + app_d) | (h < hlo - app_d)
    A = P[out]
    groups = []
    if len(A) > 50:
        vox = 0.006; lo = A.min(0)
        idx = np.floor((A - lo) / vox).astype(int)
        occ = np.zeros(idx.max(0) + 1, bool); occ[tuple(idx.T)] = True
        lab_, nl = ndimage.label(occ, structure=np.ones((3, 3, 3)))
        g = lab_[tuple(idx.T)]
        cnt = np.bincount(g, minlength=nl + 1)
        for q in np.argsort(-cnt)[:8]:
            if q == 0 or cnt[q] < 100:
                continue
            m = g == q
            ha, ra, ta = h[out][m], r[out][m], th[out][m]
            tm = np.degrees(np.angle(np.mean(np.exp(1j * ta))))
            dt = np.degrees(np.angle(np.exp(1j * (ta - np.radians(tm)))))
            groups.append(dict(points=int(cnt[q]), theta_mid_deg=round(float(tm), 1),
                               theta_span_deg=[round(float(np.percentile(dt, 2)), 1), round(float(np.percentile(dt, 98)), 1)],
                               h_mm=[round(float(np.percentile(ha, 2)) * 1e3, 1), round(float(np.percentile(ha, 98)) * 1e3, 1)],
                               r_mm=[round(float(np.percentile(ra, 2)) * 1e3, 1), round(float(np.percentile(ra, 98)) * 1e3, 1)],
                               extent_mm=[round(float(x) * 1e3, 1) for x in np.ptp(A[m], 0)]))
    # angular coverage of the body: sectors seen per height bin
    seen_frac = float(np.mean(nsec[(hc > hlo) & (hc < hhi)] / L.NSEC))
    return dict(label=lab, points_raw=int(len(P0)), points_ds=int(len(P)), sigma_mm=None if sig is None else sig * 1e3,
                app_d_mm=app_d * 1e3, axis=dict(rotcons_mm=round(cost, 3), centre=c.tolist(), dir=d.tolist(), cands=int(k)),
                cam_elev_deg=[round(float(x), 1) for x in np.percentile(el, [5, 50, 95])],
                cam_azim_deg_range=[round(float(x), 1) for x in np.percentile(az, [5, 50, 95])],
                cam_azim_cover_deg=int(np.sum(np.histogram(az, bins=36, range=(-180, 180))[0] > 0.002 * len(az)) * 10),
                n_outer=int(outer.sum()), n_inner=int(inner.sum()), two_wall_bins=int(both.sum()), t_meas_mm=t_meas,
                height_mm=round((hhi - hlo) * 1e3, 1), h_range_mm=[round(hlo * 1e3, 1), round(hhi * 1e3, 1)],
                r_out_max_mm=round(float(np.nanmax(r_out)) * 1e3, 1), body_sector_cover=round(seen_frac, 3),
                app_points=int(out.sum()), app_frac=round(float(out.mean()), 3), app_groups=groups, profile=rows)


def main():
    out = sys.argv[1]
    res = []
    for spec in sys.argv[2:]:
        lab, P, C, sig = load(spec)
        r = analyse(lab, P, C, sig)
        res.append(r)
        s = {k: v for k, v in r.items() if k not in ('profile',)}
        print(json.dumps(s))
    dirs = {r['label']: np.array(r['axis']['dir']) for r in res}
    labs = list(dirs)
    ang = {f'{a}~{b}': round(float(np.degrees(np.arccos(min(1, abs(dirs[a] @ dirs[b]))))), 2)
           for i, a in enumerate(labs) for b in labs[i + 1:]}
    print('axis angles (deg):', json.dumps(ang))
    json.dump(dict(results=res, axis_angles_deg=ang), open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
