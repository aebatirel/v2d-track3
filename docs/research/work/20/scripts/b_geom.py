# Stage B2: spoon body geometry relative to its markers, per (episode, frame), from cam a edges on table-parallel planes.
# Inputs: out/b/meas_<tag>.json (M1/M2/M3 3-D centres in the rectified-left frame, local table plane), cam a frame a[k+1].
# Table frame: n = table normal (up); u = horizontal unit axis from foot(mid(M1,M2)) to foot(M3) (bowl -> handle), refined
# by the fitted silhouette midline; w = n x u. For each station s (mm along u) and plane height h above the table, sample
# cam a (HSV) along w on the plane, walk out from the midline until the pixel leaves the wood range -> two edges
# (sub-sample crossing). The midpoint of the back-projected edges is the axis exactly at h = centreline height for a round
# (or elliptic) section; elsewhere it shifts by (hc - h) cot(alpha) with alpha the view elevation in the cross-section.
# Output: per h, the midline fit, marker lateral offsets (signed, + toward M1's side), stations from the bowl tip, widths.
# Usage: b_geom.py <tag> [k,...]
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts'); from b_lib import *
tag = sys.argv[1]; ep = int(tag.lstrip('pe')); SPL = 'public' if tag[0] == 'p' else 'evaluation'
recs = [r for r in json.load(open(f'{OUT}/meas_{tag}.json')) if r.get('triple')]
if len(sys.argv) > 2: recs = [r for r in recs if r['k'] in [int(x) for x in sys.argv[2].split(',')]]
R_a2c = R.T @ Rab; t_a2c = R.T @ (tab - T.ravel()); R_a2r = R1 @ R_a2c; t_a2r = R1 @ t_a2c
CA = t_a2r                                                   # cam a centre in rect frame
HS = [5.0, 6.0, 7.2, 8.5, 10.0, 12.0]        # plane heights (mm)
frames = read_frames(SPL, ep, 'a', [r['k'] + 1 for r in recs])


def sampler(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    def f(X):                                                  # X: (..., 3) rect frame (m) -> S, V, valid
        Xa = (X.reshape(-1, 3) - t_a2r) @ R_a2r; uv = proj_a(Xa).astype(np.float32).reshape(X.shape[:-1] + (2,))
        S = cv2.remap(hsv[..., 1], uv[..., 0], uv[..., 1], cv2.INTER_LINEAR)
        V = cv2.remap(hsv[..., 2], uv[..., 0], uv[..., 1], cv2.INTER_LINEAR)
        return S, V, uv
    return f


def is_wood(S, V): return (S > 35) & (S < 135) & (V > 160)


def edges(S, V, ws, c0):
    """Walk out from index c0 on both sides; return sub-sample w of the wood exit (or nan) and its sharpness."""
    out = []
    for step in (-1, 1):
        i = c0; core = []
        if not is_wood(S[i], V[i]): return np.nan, np.nan, np.nan, np.nan
        while 0 < i < len(S) - 1 and is_wood(S[i + step], V[i + step]): core.append(S[i]); i += step
        if not (0 < i < len(S) - 1): out += [np.nan, np.nan]; continue
        sw = np.median(core[-12:]) if core else S[i]; j2 = min(max(i + step * 8, 0), len(S) - 1)   # ~2 mm outside
        so = S[j2]; vo = V[j2]
        if so > 135:      # table: S jump; crossing of the mid level between i and i+step
            lvl = 0.5 * (sw + so); a, b = S[i], S[i + step]; f = (lvl - a) / (b - a) if b != a else 0.5
        elif vo < 160:   # dark (base, shadow): V crossing
            vw = V[i]; lvl = 0.5 * (vw + vo); a, b = V[i], V[i + step]; f = (lvl - a) / (b - a) if b != a else 0.5
        else:            # soft exit (glare / grey): reject
            out += [np.nan, np.nan]; continue
        f = np.clip(f, 0, 1); out += [ws[i] + step * f * (ws[1] - ws[0]), abs(so - sw)]
    return out[0], out[2], out[1], out[3]


res = []
for r in recs:
    img = frames[r['k'] + 1]; smp = sampler(img)
    c, n = np.array(r['plane_c']), np.array(r['plane_n']); M = np.array(r['M_r'])      # rows M1, M2, M3
    foot = lambda X: X - ((X - c) @ n)[..., None] * n
    F = foot(M); O0 = 0.5 * (F[0] + F[1]); u = F[2] - O0; u /= np.linalg.norm(u); wv = np.cross(n, u)
    ws = np.arange(-0.045, 0.045, 0.00025); ss = np.arange(-0.200, 0.200, 0.002)
    out = dict(tag=tag, k=r['k'], h_markers=[float(x) for x in r['h_mm']], per_h={})
    for h in HS:
        O, uu, wvv = O0.copy(), u.copy(), wv.copy()
        for it in range(3):
            P = O[None, None] + ss[:, None, None] * uu + ws[None, :, None] * wvv + h * 1e-3 * n
            S, V, _ = smp(P)
            L = np.full(len(ss), np.nan); Rr = np.full(len(ss), np.nan); sh = np.full((len(ss), 2), np.nan)
            for i in range(len(ss)):
                c0 = np.argmin(np.abs(ws))
                a, b, s1, s2 = edges(S[i], V[i], ws, c0); L[i], Rr[i] = a, b; sh[i] = (s1, s2)
            Mloc = np.c_[(M - O) @ uu, (M - O) @ wvv]          # marker (s, w) in this frame (m)
            wid = Rr - L; mid = 0.5 * (L + Rr)
            # midline fit over the body, excluding marker zones (+-18 mm around M1/M2 stations, beyond M3 - 10 mm)
            ok = np.isfinite(mid) & (wid > 0.008) & (wid < 0.065)
            for sm in Mloc[:2, 0]: ok &= np.abs(ss - sm) > 0.018
            ok &= ss < Mloc[2, 0] - 0.012
            if ok.sum() < 20: break
            A_ = np.c_[np.ones(ok.sum()), ss[ok]]; coef = np.linalg.lstsq(A_, mid[ok], rcond=None)[0]
            for _ in range(3):
                rr = mid[ok] - A_ @ coef; keep = np.abs(rr) < max(3 * 1.4826 * np.median(np.abs(rr)), 0.0005)
                coef = np.linalg.lstsq(A_[keep], mid[ok][keep], rcond=None)[0]
            # re-centre the frame on the fitted midline
            O = O + coef[0] * wvv; ang = np.arctan(coef[1]); uu2 = np.cos(ang) * uu + np.sin(ang) * wvv; wvv = np.cross(n, uu2); uu = uu2
            if abs(coef[0]) < 2e-5 and abs(coef[1]) < 1e-4: break
        if ok.sum() < 20: continue
        Mloc = np.c_[(M - O) @ uu, (M - O) @ wvv]
        sgn = np.sign(Mloc[0, 1])                                # + toward M1's side
        rr = mid[ok] - (A_ @ coef)
        # bowl tip: the most negative s with a valid wood centre; handle end: last valid before M3
        valid = np.isfinite(wid) & (wid > 0.004)
        tip = ss[valid].min() if valid.any() else np.nan
        prof = [(float(ss[i]), float(wid[i])) for i in range(len(ss)) if np.isfinite(wid[i])]
        # handle-only midline (stations from M2 + 20 mm to M3 - 12 mm), extrapolated to the markers; and bowl-only centre
        hm = np.isfinite(mid) & (wid > 0.012) & (wid < 0.03) & (ss > Mloc[1, 0] + 0.020) & (ss < Mloc[2, 0] - 0.012)
        bm = np.isfinite(mid) & (wid > 0.03) & (ss < Mloc[0, 0] - 0.03)
        lat_h = None; bowl_c = None
        if hm.sum() >= 10:
            ch = np.polyfit(ss[hm], mid[hm], 1); lat_h = [float(sgn * (Mloc[i, 1] - np.polyval(ch, Mloc[i, 0])) * 1e3) for i in range(3)]
            if bm.sum() >= 5: bowl_c = float(sgn * (np.median(mid[bm]) - np.polyval(ch, np.median(ss[bm]))) * 1e3)
        tip_w = None
        if hm.sum() >= 10:   # bowl tip lateral: median midline over the first 6-14 mm of valid bowl stations, vs the handle line
            vs = np.nonzero(np.isfinite(mid) & (wid > 0.004))[0]
            if len(vs):
                t0 = ss[vs[0]]; tm = np.isfinite(mid) & (ss > t0 + 0.006) & (ss < t0 + 0.014)
                if tm.sum() >= 2: tip_w = float(sgn * (np.median(mid[tm]) - np.polyval(ch, np.median(ss[tm]))) * 1e3)
        out['per_h'][str(h)] = dict(lat_handle=lat_h, bowl_vs_handleline=bowl_c, tip_vs_handleline=tip_w, n_handle=int(hm.sum()),
            mid_profile=[(float(ss[i] * 1e3), float(sgn * mid[i] * 1e3)) for i in range(len(ss)) if np.isfinite(mid[i])],
            lat=[float(sgn * Mloc[i, 1] * 1e3) for i in range(3)], st=[float((Mloc[i, 0] - tip) * 1e3) for i in range(3)],
            tip_s=float(tip * 1e3), n_fit=int(ok.sum()), mid_rms_mm=float(np.sqrt(np.mean(rr ** 2)) * 1e3),
            width_profile=prof, side_M1=int(sgn))
    # view geometry: elevation of the cam-a ray in the cross-section plane at the M1/M2 stations
    Mm = 0.5 * (M[0] + M[1]); ray = Mm - CA; ray /= np.linalg.norm(ray)
    rc_ = ray - (ray @ uu) * uu; rc_ /= np.linalg.norm(rc_)
    out['alpha_cross_deg'] = float(np.degrees(np.arcsin(abs(rc_ @ n)))); out['ray_w_sign'] = float(np.sign(rc_ @ wvv) * sgn)
    out['alpha_view_deg'] = float(np.degrees(np.arcsin(abs(ray @ n)))); out['axis_vs_view_deg'] = float(np.degrees(np.arccos(abs(ray @ uu))))
    res.append(out)
    for h in ('6.0', '7.2', '8.5'):
        if h not in out['per_h']: continue
        q = out['per_h'][h]
        print(f"{tag} k{r['k']} h{h:>4}: lat M1 {q['lat'][0]:5.1f} M2 {q['lat'][1]:5.1f} M3 {q['lat'][2]:5.1f} | st M1 {q['st'][0]:5.1f} M2 {q['st'][1]:5.1f} "
              f"M3 {q['st'][2]:5.1f} | fit n {q['n_fit']} rms {q['mid_rms_mm']:.2f} | a_x {out['alpha_cross_deg']:.0f} rw {out['ray_w_sign']:+.0f} "
              f"| handle-line lat {np.round(q['lat_handle'],1) if q['lat_handle'] else None} (n {q['n_handle']}) bowl-vs-line {q['bowl_vs_handleline']} tip-vs-line {q['tip_vs_handleline']}", flush=True)
json.dump(res, open(f'{OUT}/geom_{tag}.json', 'w'))
