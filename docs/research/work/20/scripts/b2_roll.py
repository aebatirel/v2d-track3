# Stage B re-run: roll of the spoon about its handle axis relative to the cam-a view, WITHOUT the marker depths.
# Dense b/c SGBM (dy-field rectified, b_lib.rect_pair) on (i) the bowl interior (inner part of the cam-a outline from
# b2_front) -> robust plane = bowl rim-plane proxy (symmetric dish: plane normal ~ dish axis), (ii) the handle's visible
# front surface (near and far segments, central strip) -> 3-D handle axis direction.
# Roll = angle of the view direction from the bowl normal, measured about the handle axis (+ = view ray tilted toward +y,
# i.e. the M1 side is farther). At rest the same fit is compared with the SGBM table plane (validation).
# Usage: b2_roll.py <ep> <src: held|rest> <k> [k ...]  -> out/b2/roll_e<ep>.jsonl
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts')
EP, SRC, KLIST = int(sys.argv[1]), sys.argv[2], [int(x) for x in sys.argv[3:]]
sys.argv = ['b2_front.py', str(EP)] + (['--rest'] if SRC == 'rest' else [])   # b2_front module code, empty frame list
src = open('/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts/b2_front.py').read().split('\nfor k in KS:')[0]
src = src.replace("    ok = [x for x in rows if x is not None]\n", "    ok = [x for x in rows if x is not None]; DUMP.update(ok=ok, Zs=Zs, mpu=mm_per_unit, sM=sM, nM=nM, o=o, es=es, en=en, Xa=Xa)\n")
src = src.replace("    cf = variants[best]; keep = both\n", "    cf = variants[best]; keep = both; DUMP.update(variants=variants, cL=cL, cR=cR, kL=kL, kR=kR, hw=hw, s_=s_, l_=l_, r_=r_, smm=smm, sMmm=sMmm)\n")
DUMP = {}
if SRC == 'rest':     # rest records from Stage B b_meas (table-constrained marker depths, order M1 M2 M3)
    src = src.replace("for l in open(f'{O2}/held_e{ep}.jsonl'):\n    r = json.loads(l); H[r['k']] = r",
                      "for r in json.load(open(f'{OUT}/meas_e{ep}.json')):\n    r.update(tri_n_dot_view=0.0, axis_dot_view=0.0, speed_px=[0, 0, 0]); H[r['k']] = r")
exec(compile(src, 'b2_front', 'exec'))
SG = cv2.StereoSGBM_create(minDisparity=32, numDisparities=112, blockSize=7, P1=8 * 49, P2=32 * 49, disp12MaxDiff=1,
                           uniquenessRatio=10, speckleWindowSize=100, speckleRange=2, mode=cv2.STEREO_SGBM_MODE_HH)


def a_norm_to_rect_px(xy, Z):
    """cam-a normalised coords at cam-a depth Z (m) -> rectified-left pixel."""
    Xa_ = np.c_[xy * Z[:, None], Z]; Xr = Xa_ @ R_a2r.T + t_a2r
    return np.c_[FR * Xr[:, 0] / Xr[:, 2] + CXR, FR * Xr[:, 1] / Xr[:, 2] + CYR]


def plane_fit(P, thr=0.002, it=400):
    rng = np.random.default_rng(1); best = None
    for _ in range(it):
        s3 = P[rng.choice(len(P), 3, replace=False)]; nr = np.cross(s3[1] - s3[0], s3[2] - s3[0])
        if np.linalg.norm(nr) < 1e-12: continue
        nr /= np.linalg.norm(nr); inl = np.abs((P - s3[0]) @ nr) < thr
        if best is None or inl.sum() > best.sum(): best = inl
    Q = P[best]; c = Q.mean(0); _, sv, vt = np.linalg.svd(Q - c); nr = vt[2]
    if nr @ c > 0: nr = -nr                                         # toward the camera
    return c, nr, best, float(np.sqrt(np.mean(((Q - c) @ nr) ** 2)))


for k in KLIST:
    DUMP.clear(); meas = measure(k)
    if 'err' in meas or 'variants' not in DUMP: print(EP, k, 'measure failed', meas.get('err')); continue
    ok = np.array(DUMP['ok']); Zs = DUMP['Zs']; o, es, en = DUMP['o'], DUMP['es'], DUMP['en']; mpu = DUMP['mpu']
    cf = DUMP['variants']['R-hw'] if 'R-hw' in DUMP['variants'] else list(DUMP['variants'].values())[0]
    s_, l_, r_, smm, sMmm = DUMP['s_'], DUMP['l_'], DUMP['r_'], DUMP['smm'], DUMP['sMmm']
    gb = cv2.cvtColor(read_frames(SPL if 'SPL' in dir() else 'evaluation', EP, 'b', [k])[k], cv2.COLOR_BGR2GRAY)
    gc = cv2.cvtColor(read_frames('evaluation', EP, 'c', [k])[k], cv2.COLOR_BGR2GRAY)
    rc, rbw, fdy, dinfo = rect_pair(gc, gb)
    disp = SG.compute(rc, rbw.astype(np.uint8)).astype(np.float32) / 16.0
    # bowl interior polygon (cam-a normalised -> rect c), inner part: 4 mm in from each side, tip+6 .. M1-16 mm
    w_ = (r_ - l_) * 1e3 * Zs(s_)
    bowl = (smm < sMmm[0] - 16) & (smm > smm.min() + 6) & (w_ > 20)
    def poly(sel, inset_mm):
        ss = s_[sel]; ins = inset_mm / (1e3 * Zs(ss)); L = l_[sel] + ins; Rr = r_[sel] - ins
        pts = [o + s * es + n * en for s, n in zip(np.r_[ss, ss[::-1]], np.r_[L, Rr[::-1]])]
        return np.array(pts), np.r_[ss, ss[::-1]]
    P, sp = poly(bowl, 4.0); px = a_norm_to_rect_px(P, Zs(sp))
    mask = np.zeros(rc.shape, np.uint8); cv2.fillPoly(mask, [px.round().astype(np.int32)], 1)
    yy, xx = np.nonzero((mask > 0) & (disp > 33)); d = disp[yy, xx]
    Xb = tri_rect(xx.astype(float), yy.astype(float), xx - d, yy.astype(float))
    # handle central strip (+-35% of the half-width around the R-hw axis), near & far segments
    hw = DUMP['hw']; ax_n = np.polyval(cf, s_)
    hsel = (np.abs(smm - sMmm[0]) > 14) & (np.abs(smm - sMmm[1]) > 14) & (smm > sMmm[1] + 15) & (smm < sMmm[2] - 8) & (DUMP['kR'] | DUMP['kL'])
    segs = []
    for lo, hi in ((sMmm[1] + 15, sMmm[1] + 60), (sMmm[2] - 40, sMmm[2] - 8)):
        sel = hsel & (smm >= lo) & (smm < hi)
        if sel.sum() < 5: segs.append(None); continue
        ss = s_[sel]; c_ = np.polyval(cf, ss); half = 0.35 * hw / (1e3 * Zs(ss))
        pts = [o + s * es + n * en for s, n in zip(np.r_[ss, ss[::-1]], np.r_[c_ - half, (c_ + half)[::-1]])]
        pxh = a_norm_to_rect_px(np.array(pts), Zs(np.r_[ss, ss[::-1]])); mh = np.zeros(rc.shape, np.uint8); cv2.fillPoly(mh, [pxh.round().astype(np.int32)], 1)
        y2, x2 = np.nonzero((mh > 0) & (disp > 33))
        if len(y2) < 30: segs.append(None); continue
        X2 = tri_rect(x2.astype(float), y2.astype(float), x2 - disp[y2, x2], y2.astype(float))
        Xa2 = (X2 - t_a2r) @ R_a2r; med = np.median(Xa2, 0)
        segs.append(dict(n=len(y2), centre_a=med.tolist(), s_mm=float(np.median(smm[sel]))))
    rec = dict(k=k, src=SRC, n_bowl_px=int(len(yy)), dy_rms=dinfo['rms'])
    if len(yy) > 300:
        c, nr, inl, rms = plane_fit(Xb); nr_a = R_a2r.T @ nr; c_a = (c - t_a2r) @ R_a2r      # to cam a frame
        rec.update(bowl_plane_rms_mm=rms * 1e3, bowl_inl=float(inl.mean()), bowl_n_a=nr_a.tolist(), bowl_c_a=c_a.tolist())
        # handle axis direction in cam a: image axis line back-projected; depth from the two segments if both exist
        if segs[0] and segs[1]:
            A0, A1 = np.array(segs[0]['centre_a']), np.array(segs[1]['centre_a']); t = A1 - A0; t /= np.linalg.norm(t)
            rec['axis_src'] = 'sgbm2seg'
        else:
            M = DUMP['Xa']; t = M[2] - 0.5 * (M[0] + M[1]); t /= np.linalg.norm(t); rec['axis_src'] = 'markers'
        v = c_a / np.linalg.norm(c_a)                                  # view ray to the bowl centre
        # body frame: z = t, x = bowl normal orthogonalised to t (toward camera), y = z x x oriented to M1's image side
        xb = nr_a - (nr_a @ t) * t; xb /= np.linalg.norm(xb); yb = np.cross(t, xb)
        M = DUMP['Xa']
        if (M[0] - 0.5 * (M[0] + M[1])) @ yb < 0 and False: pass
        # orient y toward M1: use the image-plane side of M1 relative to the axis (robust to M1 depth): project yb to the image
        p0 = 0.5 * (M[0] + M[1]); img = lambda X: X[:2] / X[2]
        side_y = (img(p0 + 0.01 * yb) - img(p0)) @ en
        if side_y < 0: yb = -yb
        roll = float(np.degrees(np.arctan2(v @ yb, -(v @ xb))))     # + : ray tilted toward +y (M1 side farther)
        pitch = float(np.degrees(np.arcsin(np.clip(v @ t, -1, 1))))
        rec.update(roll_deg=roll, axis_view_deg=pitch, segs=segs)
        if segs[0]:
            S0 = np.array(segs[0]['centre_a']); A0 = S0 + (hw * 1e-3) * S0 / np.linalg.norm(S0)      # axis point at the near segment
            Mx = DUMP['Xa']; mk = []
            for j in range(3):
                q = Mx[j] - A0; q -= (q @ t) * t                       # perpendicular from the axis line
                vj = Mx[j] / np.linalg.norm(Mx[j]); lat = np.cross(t, vj); lat /= np.linalg.norm(lat)
                if lat @ yb < 0: lat = -lat
                mk.append(dict(rho=float(np.linalg.norm(q) * 1e3), lat=float(q @ lat * 1e3), tocam=float(-(q @ vj) * 1e3),
                               body_y=float(q @ yb * 1e3), body_x=float(q @ xb * 1e3)))
            rec['markers_axis'] = mk
        if SRC == 'rest':
            tn = np.array(H[k]['plane_n'] if 'plane_n' in H[k] else H[min(H)]['plane_n']); tn_a = R_a2r.T @ tn
            # bowl normal vs table normal: roll about the axis and pitch along it
            tz = t - (t @ tn_a) * tn_a; tz /= np.linalg.norm(tz); ty = np.cross(tn_a, tz)
            if ty @ yb < 0: ty = -ty
            rec.update(bowl_vs_table_roll_deg=float(np.degrees(np.arctan2(nr_a @ ty, nr_a @ tn_a))),
                       bowl_vs_table_pitch_deg=float(np.degrees(np.arctan2(nr_a @ tz, nr_a @ tn_a))),
                       axis_vs_table_deg=float(np.degrees(np.arcsin(np.clip(t @ tn_a, -1, 1)))))
    with open(f'{O2}/roll_e{EP}.jsonl', 'a') as f: f.write(json.dumps(rec) + '\n')
    if 'markers_axis' in rec: print('   markers vs 3-D axis (rho, lat, tocam | body y, x):', ' ; '.join('%.1f %+.1f %+.1f | %+.1f %+.1f' % (m['rho'], m['lat'], m['tocam'], m['body_y'], m['body_x']) for m in rec['markers_axis']))
    print(EP, k, SRC, {kk: (round(v, 2) if isinstance(v, float) else v) for kk, v in rec.items() if kk not in ('bowl_n_a', 'bowl_c_a', 'segs', 'markers_axis')}, flush=True)
