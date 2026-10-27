"""CPU audit, stage 3: join MediaPipe detections (hand_detect.py) with GT carry segments (gt_objects.py).
For every carry segment: fraction of frames with >= 1 detected hand, with 2 hands when two objects move at once,
the longest detection gap inside the segment (pipeline/hands_mp.py interpolates gaps <= 15 frames and HOLDS the hand
in place beyond that, so a long gap during a carry leaves the reference hand behind the moving object), and raw
handedness-label flips. GT row k <-> colour frame k + 1 (hands_mp.py a_offset default). Diagnostics only.
Usage: python carry_coverage.py <gt_objects.json> <det dir with episode_*.npz> > carry_coverage.txt
"""
import json, sys
import numpy as np

A_OFFSET, MAX_GAP = 1, 15
gt = json.load(open(sys.argv[1])); det_dir = sys.argv[2]
rows, tot = [], dict(carry=0, det1=0, sim=0, det2=0)
print("ep obj      seg        dur_s  lift_cm  >=1hand  longest_gap  gap>15")
for ep, info in gt.items():
    d = np.load(f"{det_dir}/episode_{int(ep):06d}.npz")
    nh = d["n_hands"].astype(int)
    T = info["frames"]
    n_k = np.array([nh[k + A_OFFSET] if k + A_OFFSET < len(nh) else 0 for k in range(T)])
    moving_any = np.zeros(T, int)
    for o, segs in info["carries"].items():
        for c in segs:
            moving_any[c["start"]:c["end"] + 1] += 1
    sim = moving_any >= 2
    tot["sim"] += int(sim.sum()); tot["det2"] += int((n_k[sim] >= 2).sum())
    for o, segs in info["carries"].items():
        for c in segs:
            s, e = c["start"], c["end"]
            seg = n_k[s:e + 1] >= 1
            gaps, run = [], 0
            for ok in seg:
                run = 0 if ok else run + 1
                gaps.append(run)
            lg = max(gaps) if gaps else 0
            tot["carry"] += len(seg); tot["det1"] += int(seg.sum())
            rows.append((int(ep), o, s, e, c["dur_s"], c["lift_cm"], float(seg.mean()), lg))
            print(f"{int(ep):>2} {o[:14]:<14} {s:>3}-{e:<3} {c['dur_s']:>5}  {c['lift_cm']:>6}  {seg.mean():7.2f}  "
                  f"{lg:>11}  {'YES' if lg > MAX_GAP else ''}")
    # raw handedness flips between consecutive frames with 2 hands (sorted by image x)
lab_flips = []
for ep in gt:
    d = np.load(f"{det_dir}/episode_{int(ep):06d}.npz")
    L, lm, nh = d["labels"], d["landmarks"], d["n_hands"]
    prev, flips, pairs = None, 0, 0
    for i in range(len(nh)):
        if nh[i] == 2:
            order = np.argsort([np.nanmean(lm[i, 0, :, 0]), np.nanmean(lm[i, 1, :, 0])])
            cur = tuple(L[i][order])
            if prev is not None:
                pairs += 1; flips += cur != prev
            prev = cur
    lab_flips.append((int(ep), flips, pairs))
print()
print(f"carry frames with >= 1 detected hand: {tot['det1']}/{tot['carry']} = {tot['det1'] / max(tot['carry'], 1):.3f}")
print(f"frames with two objects moving and 2 hands detected: {tot['det2']}/{tot['sim']}")
print(f"carry segments with a detection gap > {MAX_GAP} frames: {sum(r[7] > MAX_GAP for r in rows)}/{len(rows)}; "
      f"longest gap {max(r[7] for r in rows)} frames")
print("raw handedness label changes between consecutive 2-hand frames (left-to-right image order), per episode:")
print("  " + ", ".join(f"ep{e}: {f}/{p}" for e, f, p in lab_flips))
