"""Automatic per-clip statistics (no labels): head motion = median LK flow of corner features between consecutive
frames at 1/4 resolution (px/frame at 507 px width); sharpness = variance of Laplacian at 1/4 res.
usage: clipstats.py tag video ... ; appends one line per clip to clipstats.out and per-frame arrays to npz."""
import sys, cv2, numpy as np
args = sys.argv[1:]
for tag, vid in zip(args[0::2], args[1::2]):
    cap = cv2.VideoCapture(vid); prev = None; flow = []; sharp = []
    while True:
        ok, fr = cap.read()
        if not ok: break
        g = cv2.cvtColor(cv2.resize(fr, (507, 380), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        sharp.append(cv2.Laplacian(g, cv2.CV_64F).var())
        if prev is not None:
            p0 = cv2.goodFeaturesToTrack(prev, 300, 0.01, 8)
            if p0 is None: flow.append(np.nan)
            else:
                p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, p0, None, winSize=(21, 21), maxLevel=3)
                d = np.linalg.norm((p1 - p0).reshape(-1, 2)[st.ravel() == 1], axis=1)
                flow.append(np.median(d) if len(d) > 20 else np.nan)
        prev = g
    flow = np.array(flow); sharp = np.array(sharp); n = len(sharp)
    rel = sharp / np.median(sharp)
    np.savez(f'clip_{tag}.npz', flow=flow, sharp=sharp)
    line = (f"{tag} n={n} flow_med={np.nanmedian(flow):.2f} p90={np.nanpercentile(flow,90):.2f} "
            f"max={np.nanmax(flow):.1f} sharp_med={np.median(sharp):.0f} frac_rel<0.5={np.mean(rel<0.5):.2f} "
            f"frac_rel<0.3={np.mean(rel<0.3):.2f}")
    print(line, flush=True); open('clipstats.out', 'a').write(line + '\n')
