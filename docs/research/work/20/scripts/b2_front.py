# Stage B re-run: in-plane spoon geometry from a near-frontal (held, concave face toward cam a) frame.
# Cam a only for the outline (one exposure); b/c only through the marker 3-D positions (held record) for depth/scale/tilt.
#  1. straightened image: rows = station s along the approx. axis (mid(M1,M2) -> M3), cols = perpendicular offset n,
#     sampled in UNDISTORTED normalised cam-a coordinates (full 14-coef model) so straight 3-D lines stay straight;
#  2. per row: outline edges in the saturation channel (wood S low, table S high), 50% crossing between local levels;
#  3. handle rows (constant width ~ 2r, away from markers/hand) -> robust line = image of the handle axis;
#  4. bowl rows: outline midline offset from that line vs station; markers' perpendicular offsets; all converted to mm by
#     the local depth (marker depths interpolated along the axis).
# No GT, no hand labels. Usage: b2_front.py <ep> <k> [k ...] [--dbg]   -> out/b2/front_e<ep>.jsonl (+ dbg png)
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts'); from b_lib import *
O2 = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b2'
args = [a for a in sys.argv[1:] if not a.startswith('--')]; DBG = '--dbg' in sys.argv
ep = int(args[0]); KS = [int(x) for x in args[1:]]
H = {}; REST = '--rest' in sys.argv
if REST:   # rest records from Stage B b_meas (table-constrained marker depths; order M1 M2 M3)
    for r in json.load(open(f'{OUT}/meas_e{ep}' + ('_end' if '--end' in sys.argv else '') + '.json')):
        if r.get('M_r') is not None and len(r['M_r']) == 3:
            r.update(tri_n_dot_view=0.0, axis_dot_view=0.0, speed_px=[0, 0, 0]); H[r['k']] = r
else:
    for l in open(f'{O2}/held_e{ep}.jsonl'):
        r = json.loads(l); H[r['k']] = r
R_a2c = R.T @ Rab; t_a2c = R.T @ (tab - T.ravel()); R_a2r = R1 @ R_a2c; t_a2r = R1 @ t_a2c
FA = Ka[0, 0]
STEP = 0.5 / FA                      # grid step in normalised units (~0.5 px)
SPANMIN = float(next((a.split('=')[1] for a in sys.argv if a.startswith('--span=')), 60))


def to_a(Xr): return (np.asarray(Xr) - t_a2r) @ R_a2r          # rect-left frame -> cam a frame


def norm_to_dist(xy):
    p, _ = cv2.projectPoints(np.c_[xy, np.ones(len(xy))].reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, da)
    return p.reshape(-1, 2)


def edge50(p, i0, step, lvl_in, lvl_out):
    """First crossing of the 50% level walking from i0 in direction step; returns sub-sample position or None."""
    thr = 0.5 * (lvl_in + lvl_out); i = i0
    while 0 < i + step < len(p) and p[i + step] < thr: i += step
    if not (6 < i + step < len(p) - 7): return None
    j = i + step; a, b = p[i], p[j]
    if b == a: return None
    return i + step * (thr - a) / (b - a)


def measure(k):
    h = H[k]; M = np.array(h['M_r']); Xa = to_a(M); n_m = Xa[:, :2] / Xa[:, 2:]   # markers in normalised cam-a coords
    A = read_frames('evaluation', ep, 'a', [k + 1])[k + 1]; hsv = cv2.cvtColor(A, cv2.COLOR_BGR2HSV)
    S = hsv[..., 1].astype(np.float32); V = hsv[..., 2].astype(np.float32)
    o = 0.5 * (n_m[0] + n_m[1]); es = n_m[2] - o; Ls = np.linalg.norm(es); es /= Ls; en = np.array([-es[1], es[0]])
    if (n_m[0] - o) @ en < 0: en = -en                       # +n toward M1's side
    Zs = lambda s: np.interp(s, [(n_m[0] - o) @ es, (n_m[2] - o) @ es], [0.5 * (Xa[0, 2] + Xa[1, 2]), Xa[2, 2]])  # approx depth vs s
    mm_per_unit = 1e3 * Zs(0.0)
    s_lo, s_hi = -0.180 / Zs(0.0), Ls + 0.010 / Xa[2, 2]; n_half = 0.045 / Zs(0.0)
    ss = np.arange(s_lo, s_hi, STEP); nn = np.arange(-n_half, n_half, STEP)
    G = o[None, None] + ss[:, None, None] * es + nn[None, :, None] * en
    D = norm_to_dist(G.reshape(-1, 2)).reshape(len(ss), len(nn), 2).astype(np.float32)
    Sst = cv2.remap(S, D[..., 0], D[..., 1], cv2.INTER_LINEAR, borderValue=255)
    Vst = cv2.remap(V, D[..., 0], D[..., 1], cv2.INTER_LINEAR, borderValue=0)
    Sst = cv2.GaussianBlur(Sst, (0, 0), 1.0)
    i0 = len(nn) // 2; rows = []
    sM = (n_m - o) @ es; nM = (n_m - o) @ en
    for r in range(len(ss)):
        p = Sst[r]; c0 = i0 + int(round(np.interp(ss[r], [sM[0], sM[2]], [0, 0]) / STEP))
        win = p[c0 - 3:c0 + 4]
        if win.max() > 110: rows.append(None); continue        # not wood at the centre (hand/marker/background)
        lin = float(np.median(win)); lout = float(np.percentile(np.r_[p[:15], p[-15:]], 50))
        if lout - lin < 50: rows.append(None); continue
        eL = edge50(p, c0, -1, lin, lout); eR = edge50(p, c0, +1, lin, lout)
        if eL is None or eR is None: rows.append(None); continue
        # local-level refinement (levels 4-10 samples inside/outside the first crossing)
        out = []
        for e, sg in ((eL, -1), (eR, 1)):
            ie = int(round(e))
            inside = [ie - sg * j for j in range(3, 11)]; outside = [ie + sg * j for j in range(3, 11)]
            li = float(np.median(p[inside])); lo = float(np.median(p[outside]))
            e2 = edge50(p, ie - sg * 3, sg, li, lo); out.append(e2 if e2 is not None else e)
        rows.append((ss[r], nn[0] + out[0] * STEP, nn[0] + out[1] * STEP, lin, lout))
    ok = [x for x in rows if x is not None]
    if len(ok) < 50: return dict(k=k, err='few rows %d' % len(ok))
    Rr = np.array(ok); s_, l_, r_ = Rr[:, 0], Rr[:, 1], Rr[:, 2]; w_ = (r_ - l_) * 1e3 * Zs(s_); m_ = 0.5 * (l_ + r_)
    smm = s_ * mm_per_unit; sMmm = sM * mm_per_unit
    # handle candidate rows: past M2 + 15 mm, before M3 - 8 mm, not within 14 mm of the M1/M2 stations
    cand = (smm > sMmm[1] + 15) & (smm < sMmm[2] - 8)
    for j in range(2): cand &= np.abs(smm - sMmm[j]) > 14
    # each limb robustly on its own (edges in normalised units; residual gate 0.5 mm); occluded rows drop out per limb
    def limb(e, sign):
        """RANSAC line on the candidate rows (inlier gate 0.4 mm), plausible: |slope| < 0.08, edge 4-16 mm from the reference
        line on its own side; score = inliers + span bonus; LSQ refit on inliers."""
        idx = np.nonzero(cand)[0]
        if len(idx) < 8: return None, np.zeros(len(s_), bool)
        zz = 1e3 * Zs(s_); rng = np.random.default_rng(0); best = (-1, None)
        for _ in range(600):
            i, j = rng.choice(idx, 2, replace=False)
            if abs(s_[i] - s_[j]) * mm_per_unit < 10: continue
            c_ = np.polyfit(s_[[i, j]], e[[i, j]], 1)
            if abs(c_[0]) > 0.08 or not (4 < sign * np.polyval(c_, 0.0) * zz.mean() < 16): continue
            inl = cand & (np.abs((e - np.polyval(c_, s_)) * zz) < 0.4)
            sc = inl.sum() + 0.3 * np.ptp(smm[inl]) if inl.sum() > 1 else 0
            if sc > best[0]: best = (sc, inl)
        if best[1] is None: return None, np.zeros(len(s_), bool)
        kp = best[1]
        for _ in range(3):
            c_ = np.polyfit(s_[kp], e[kp], 1); kp = cand & (np.abs((e - np.polyval(c_, s_)) * zz) < 0.4)
        return np.polyfit(s_[kp], e[kp], 1), kp
    cL, kL = limb(l_, -1); cR, kR = limb(r_, +1)
    span = lambda kp: float(np.ptp(smm[kp])) if kp.sum() > 1 else 0.0
    both = kL & kR
    if both.sum() < 6 or (cL is None and cR is None): return dict(k=k, err='few handle rows (both limbs) %d' % both.sum())
    hw = float(np.median((r_[both] - l_[both]) * 1e3 * Zs(s_[both]))) / 2          # handle half-width, mm
    spL, spR = span(kL), span(kR)
    variants = {}
    if spL > SPANMIN and spR > SPANMIN: variants['mid'] = 0.5 * (cL + cR)
    if spR > SPANMIN: variants['R-hw'] = cR - np.array([0, hw / (1e3 * Zs(np.median(s_[both])))])
    if spL > SPANMIN: variants['L+hw'] = cL + np.array([0, hw / (1e3 * Zs(np.median(s_[both])))])
    # midpoint line over the whole handle (rows with both edges, width 14-24 mm, trimmed at 0.6 mm): exact for a round rod
    # even when it bulges (symmetric width change); needs a long both-limb span (rest frames)
    mp = cand & (w_ > 14) & (w_ < 24)
    if mp.sum() > 20 and np.ptp(smm[mp]) > SPANMIN:
        kp = mp.copy()
        for _ in range(4):
            c_ = np.polyfit(s_[kp], m_[kp], 1); rr = (m_ - np.polyval(c_, s_)) * 1e3 * Zs(s_); kp = mp & (np.abs(rr) < 0.6)
        variants['midpts'] = np.polyfit(s_[kp], m_[kp], 1); MPINFO = dict(n=int(kp.sum()), span=float(np.ptp(smm[kp])), rms=float(np.sqrt(np.mean(rr[kp] ** 2))))
    else: MPINFO = None
    if not variants: return dict(k=k, err='no limb spans 60 mm (L %.0f R %.0f)' % (spL, spR))
    best = 'midpts' if 'midpts' in variants else 'mid' if 'mid' in variants else ('R-hw' if spR >= spL and 'R-hw' in variants else 'L+hw')
    cf = variants[best]; keep = both
    hs = smm[kL | kR]
    res_mm = (np.r_[(l_ - np.polyval(cL, s_))[kL], (r_ - np.polyval(cR, s_))[kR]] * 1e3 * np.r_[Zs(s_[kL]), Zs(s_[kR])]) if (cL is not None and cR is not None) else np.zeros(1)
    # bowl: rows before M1 - 12 mm; outline midline offsets from the axis line (mm, + toward M1)
    def offs(c_): return (m_ - np.polyval(c_, s_)) * 1e3 * Zs(s_)
    off = offs(cf)
    bowl = (smm < sMmm[0] - 12) & (w_ > 20)
    sb, ob, wb = smm[bowl], off[bowl], w_[bowl]
    # 3-D roll from the markers: Kabsch of the rest layout (y lat +M1, x toward concave, s along axis; mm) onto stereo M (cam a)
    Bd = np.array([[18.9, 6.0, 0.0], [-15.9, 10.0, 39.8], [-2.0, 11.0, 192.4]])
    Pa = Xa * 1e3; Bc, Pc = Bd - Bd.mean(0), Pa - Pa.mean(0); U_, _, Vt_ = np.linalg.svd(Bc.T @ Pc); dd = np.sign(np.linalg.det(U_ @ Vt_))
    Rk = (U_ @ np.diag([1, 1, dd]) @ Vt_).T                                  # body -> cam a
    xb = Rk[:, 1]; zb = Rk[:, 2]; vdir = Pa.mean(0) / np.linalg.norm(Pa.mean(0))
    roll_deg = float(np.degrees(np.arctan2(-(Rk[:, 0] @ vdir), -(xb @ vdir))))   # rotation of the concave normal about s, + = concave turns toward +y (M1)
    kab_rms = float(np.sqrt(np.mean(np.sum((Bc @ Rk.T - Pc) ** 2, 1))))
    out = dict(k=k, front=h['tri_n_dot_view'], ax_view=h['axis_dot_view'], speed=h['speed_px'], n_rows=len(ok),
               axis_variant=best, midpts_info=MPINFO, variants={kk: [float(v) for v in vv] for kk, vv in variants.items()},
               n_L=int(kL.sum()), n_R=int(kR.sum()), span_L=spL, span_R=spR, n_both=int(both.sum()), handle_hw_mm=hw,
               limb_res_mm=float(np.sqrt(np.mean(res_mm ** 2))), handle_s_mm=[float(hs.min()), float(hs.max())],
               limb_angle_deg=float(np.degrees(np.arctan(cR[0]) - np.arctan(cL[0]))) if (cL is not None and cR is not None) else None,
               mm_per_unit=float(mm_per_unit), markers_s_mm=sMmm.tolist(), roll_kabsch_deg=roll_deg, kabsch_rms_mm=kab_rms,
               markers_off_mm=[float((nM[j] - np.polyval(cf, sM[j])) * 1e3 * Zs(sM[j])) for j in range(3)],
               markers_off_var={kk: [float((nM[j] - np.polyval(vv, sM[j])) * 1e3 * Zs(sM[j])) for j in range(3)] for kk, vv in variants.items()},
               bowl_s=sb.tolist(), bowl_off=ob.tolist(), bowl_w=wb.tolist(),
               bowl_off_var={kk: offs(vv)[bowl].tolist() for kk, vv in variants.items()})
    if len(sb) > 20:
        tip = sb.min(); wmax = sb[np.argmax(wb)]
        sel = lambda a, b: (sb >= tip + a) & (sb < tip + b)
        out.update(tip_s=float(tip), wmax_s=float(wmax), wmax=float(wb.max()),
                   off_tip=float(np.median(ob[sel(3, 15)])) if sel(3, 15).sum() else None,
                   off_15_45=float(np.median(ob[sel(15, 45)])) if sel(15, 45).sum() else None,
                   off_45_75=float(np.median(ob[sel(45, 75)])) if sel(45, 75).sum() else None,
                   off_area=float(np.sum(ob * wb) / np.sum(wb)))         # width-weighted mean offset (area centroid shift)
    out['off_var'] = {}
    for kk, vv in variants.items():
        ov = offs(vv)[bowl]
        if len(sb) > 20:
            tip = sb.min(); sel = lambda a, b: (sb >= tip + a) & (sb < tip + b)
            out['off_var'][kk] = dict(tip=float(np.median(ov[sel(3, 15)])), c15_45=float(np.median(ov[sel(15, 45)])), c45_75=float(np.median(ov[sel(45, 75)])),
                                      area=float(np.sum(ov * wb) / np.sum(wb)))
    if DBG:
        vis = cv2.cvtColor(np.clip(Vst, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        for (s0, l0, r0, *_ ) in ok:
            rr = int(round((s0 - ss[0]) / STEP)); cv2.circle(vis, (int(round((l0 - nn[0]) / STEP)), rr), 0, (0, 0, 255), -1); cv2.circle(vis, (int(round((r0 - nn[0]) / STEP)), rr), 0, (0, 255, 0), -1)
        for rr in range(0, len(ss), 2):
            cc = (np.polyval(cf, ss[rr]) - nn[0]) / STEP; cv2.circle(vis, (int(round(cc)), rr), 0, (255, 255, 0), -1)
        for s0, l0, r0, a1, a2 in zip(s_, l_, r_, kL, kR):
            if a1: cv2.circle(vis, (int(round((l0 - nn[0]) / STEP)), int(round((s0 - ss[0]) / STEP))), 1, (255, 0, 255), -1)
            if a2: cv2.circle(vis, (int(round((r0 - nn[0]) / STEP)), int(round((s0 - ss[0]) / STEP))), 1, (255, 0, 255), -1)
        cv2.imwrite(f'{O2}/front{"rest" if REST else ""}_e{ep}_k{k}.png', np.rot90(vis).copy())
    return out


for k in KS:
    o = measure(k)
    with open(f'{O2}/front{"rest" if REST else ""}_e{ep}.jsonl', 'a') as f: f.write(json.dumps(o) + '\n')
    if 'err' in o: print(ep, k, o['err']); continue
    print(f"e{ep} k{k} front {o['front']:.2f} roll {o['roll_kabsch_deg']:+.1f} (kab {o['kabsch_rms_mm']:.1f}) | {o['axis_variant']} L {o['n_L']}/{o['span_L']:.0f} R {o['n_R']}/{o['span_R']:.0f} both {o['n_both']} "
          f"hw {o['handle_hw_mm']:.2f} res {o['limb_res_mm']:.2f} ang {o['limb_angle_deg']} | markers off " + ' '.join(f'{x:+.1f}' for x in o['markers_off_mm']) +
          f" | bowl tip {o.get('tip_s', 0):.0f} wmax {o.get('wmax', 0):.1f}@{o.get('wmax_s', 0):.0f} off tip {o.get('off_tip')} 15-45 {o.get('off_15_45')} 45-75 {o.get('off_45_75')} area {o.get('off_area')} | var " + json.dumps({kk: {a: round(b, 2) for a, b in v.items()} for kk, v in o['off_var'].items()}), flush=True)
