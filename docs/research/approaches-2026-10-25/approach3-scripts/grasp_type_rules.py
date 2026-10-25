"""Rule-based GRASP-taxonomy family per hold phase, from OUR reference only (no ground truth), plus a noise test.

Holds: pipeline/hold_phases.py (the same holds grasp-lock uses). Two feature sources per frame of a hold:
  R  the reference's 16 contact slots on the held object (robot sites after E2S IK; slot order = mkref PROBE_SITES:
     tips, DPs, thumb MCP / finger MPs, palm), contact = slot active;
  H  the perceived human hand (mano_<s>_joints, MediaPipe order) against our mesh: a digit touches when one of its
     joints (tip, DIP, PIP) is within 1.5 cm of the surface (joint centres sit ~0.7 cm under the skin), the palm when
     the palm centre (mean of wrist + 4 MCPs) is within 2.5 cm.
Features: thumb / finger / palm contact; opposition angle = angle between the mean outward surface normal under the
thumb and under the fingers (Feix: VF1 opposes VF2); opposition axis (thumb contacts -> finger contacts) in the human
hand frame (x distal = wrist->middle MCP, z volar, y radial); world-z of the finger contact normals (fingers under /
on top). Family rules (Feix et al. 2016 Fig. 1 opposition types, VF assignment; Bullock 2013 non-prehensile):
  power      palm contact + >= 2 fingers opposing the palm or the thumb (normal angle >= 110 deg)
  side       thumb opposes fingers (>= 110 deg), no palm, opposition axis mostly along the hand's radial (y) axis
  pad2/pad3/pad45  thumb opposes 1 / 2 / >= 3 fingers (>= 110 deg), no palm, axis not mostly radial
  under      no opposition, contacts on the object's underside (normals down): platform / hook (gravity-dependent)
  top        no opposition, contacts on the top (normals up): flat-hand push / drag (non-prehensile)
  one-sided  contacts without opposition, neither under nor top
Per hold: per-frame labels, a 7-frame mode filter, stages = runs >= 6 frames; label = the most frequent stage label.
Noise test (H only): the human joints get a per-hand rigid offset (AR(1), time constant 5 frames, sd SIGMA) + iid
0.5 cm per joint; agreement of per-frame and per-hold labels with the unperturbed ones over SEEDS seeds.
Usage: python -I grasp_type_rules.py OUT.json TAG=REF.parquet [TAG=REF.parquet ...]
"""
import json, os, sys
from collections import Counter
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_ref, Surface, to_obj, hold_list  # noqa: E402

DIG = {'thumb': [0, 5, 10], 'index': [1, 6, 11], 'middle': [2, 7, 12], 'ring': [3, 8, 13], 'pinky': [4, 9, 14]}
HJ = {'thumb': [4, 3, 2], 'index': [8, 7, 6], 'middle': [12, 11, 10], 'ring': [16, 15, 14], 'pinky': [20, 19, 18]}
PALM = [0, 5, 9, 13, 17]
D_DIG, D_PALM, OPP = 0.015, 0.025, 110.0
SIGMAS, SEEDS = (0.01, 0.02), 4


def hand_frame(J, side):
    x = J[9] - J[0]; x /= np.linalg.norm(x) + 1e-9
    z = np.cross(J[5] - J[0], J[17] - J[0]) * (1 if side == 'right' else -1)
    z -= (z @ x) * x; z /= np.linalg.norm(z) + 1e-9
    y = np.cross(z, x) * (1 if side == 'right' else -1)       # radial (thumb side)
    return np.stack([x, y, z])


def classify(thumb, fingers, palm, nT, nF, nP, axis_h, nz_f):
    """thumb/fingers/palm: contact flags/count; nT, nF, nP: mean outward normals (world) or None; axis_h: opposition
    axis in the hand frame or None; nz_f: world z of the mean finger-contact normal."""
    ang = lambda a, b: np.degrees(np.arccos(np.clip(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9), -1, 1)))
    if palm and fingers >= 2 and ((nP is not None and nF is not None and ang(nP, nF) >= OPP) or
                                  (thumb and nT is not None and nF is not None and ang(nT, nF) >= OPP)):
        return 'power'
    if thumb and fingers >= 1 and nT is not None and nF is not None and ang(nT, nF) >= OPP:
        if axis_h is not None and abs(axis_h[1]) > max(abs(axis_h[0]), abs(axis_h[2])):
            return 'side'
        return 'pad2' if fingers == 1 else 'pad3' if fingers == 2 else 'pad45'
    if fingers + thumb + palm == 0:
        return 'none'
    if nz_f is not None and nz_f < -0.5:
        return 'under'
    if nz_f is not None and nz_f > 0.5:
        return 'top'
    return 'one-sided'


def mode_filter(lab, w=7):
    out = list(lab)
    for i in range(len(lab)):
        win = lab[max(0, i - w // 2):i + w // 2 + 1]
        out[i] = Counter(win).most_common(1)[0][0]
    return out


def stages(lab, min_len=6):
    runs, s = [], 0
    for i in range(1, len(lab) + 1):
        if i == len(lab) or lab[i] != lab[s]:
            runs.append([lab[s], s, i]); s = i
    keep = [r for r in runs if r[2] - r[1] >= min_len] or [max(runs, key=lambda r: r[2] - r[1])]
    merged = [keep[0]]
    for r in keep[1:]:
        if r[0] == merged[-1][0]:
            merged[-1][2] = r[2]
        else:
            merged.append(r)
    return merged


def frame_R(d, side, j, f, surf):
    pid = d[f'pid_{side}'][f]; on = pid == j + 1
    # outward normals at the robot sites' nearest surface points (slot positions are on the surface)
    from common import PROBE_SITES, PALM_FRAMES
    F = d[f'F_{side}']
    sites = np.stack([F[k][f] for k in PROBE_SITES] + [np.mean([F[k][f] for k in PALM_FRAMES], 0)])
    _, cp, n_o = surf.query(to_obj(d, j, f, sites)); n_w = d['OR'][j][f].apply(n_o); c_w = d['OR'][j][f].apply(cp) + d['OP'][f, j]
    th = on[DIG['thumb']].any(); fi = [g for g in DIG if g != 'thumb' and on[DIG[g]].any()]; pa = bool(on[15])
    sel = lambda ks: [k for k in ks if on[k]]
    tk = sel(DIG['thumb']); fk = sel(sum((DIG[g] for g in fi), []))
    nT = n_w[tk].mean(0) if tk else None; nF = n_w[fk].mean(0) if fk else None; nP = n_w[15] if pa else None
    Hf = hand_frame(d[f'J_{side}'][f], side)
    axis = Hf @ (c_w[fk].mean(0) - c_w[tk].mean(0)) if tk and fk else None
    nz = nF[2] / (np.linalg.norm(nF) + 1e-9) if nF is not None else (nP[2] if nP is not None else None)
    return classify(th, len(fi), pa, nT, nF, nP, axis, nz), dict(thumb=bool(th), fingers=fi, palm=pa)


def frame_H(J, side, d, j, f, surf):
    X = to_obj(d, j, f, J); dist, cp, n_o = surf.query(X)
    n_w = d['OR'][j][f].apply(n_o); c_w = d['OR'][j][f].apply(cp) + d['OP'][f, j]
    pc = J[PALM].mean(0); dpc, cpp, npp = surf.query(to_obj(d, j, f, pc[None]))
    on = {g: [k for k in HJ[g] if dist[k] < D_DIG] for g in HJ}
    th = bool(on['thumb']); fi = [g for g in HJ if g != 'thumb' and on[g]]; pa = bool(dpc[0] < D_PALM)
    tk = on['thumb']; fk = sum((on[g] for g in fi), [])
    nT = n_w[tk].mean(0) if tk else None; nF = n_w[fk].mean(0) if fk else None
    nP = d['OR'][j][f].apply(npp[0]) if pa else None
    axis = hand_frame(J, side) @ (c_w[fk].mean(0) - c_w[tk].mean(0)) if tk and fk else None
    nz = nF[2] / (np.linalg.norm(nF) + 1e-9) if nF is not None else (nP[2] if nP is not None else None)
    OPP_LOG.append(np.degrees(np.arccos(np.clip(nT @ nF / (np.linalg.norm(nT) * np.linalg.norm(nF) + 1e-9), -1, 1)))
                   if nT is not None and nF is not None else np.nan)
    return classify(th, len(fi), pa, nT, nF, nP, axis, nz)


OPP_LOG = []


def ar1(T, sd, tau, rng):
    a = np.exp(-1.0 / tau); e = np.zeros((T, 3)); e[0] = rng.normal(0, sd, 3)
    for t in range(1, T):
        e[t] = a * e[t - 1] + rng.normal(0, sd * np.sqrt(1 - a * a), 3)
    return e


def main(out, specs):
    res = []
    for spec in specs:
        tag, path = spec.split('=', 1); d = load_ref(path); surf = {n: Surface(n) for n in d['names']}
        for ph in hold_list(path):
            s, o, a, b = ph['hand'], ph['object'], ph['start'], ph['end']; j = d['names'].index(o)
            fr = range(a, b)
            labR, info = zip(*[frame_R(d, s, j, f, surf[o]) for f in fr])
            OPP_LOG.clear(); labH = [frame_H(d[f'J_{s}'][f], s, d, j, f, surf[o]) for f in fr]
            oa = np.array(OPP_LOG, float); both = np.isfinite(oa)
            stR, stH = stages(mode_filter(list(labR))), stages(mode_filter(labH))
            share = dict(thumb=round(float(np.mean([i['thumb'] for i in info])), 2),
                         palm=round(float(np.mean([i['palm'] for i in info])), 2),
                         fingers_mean=round(float(np.mean([len(i['fingers']) for i in info])), 2))
            def top(st):
                tot = Counter()
                for r in st:
                    tot[r[0]] += r[2] - r[1]
                return tot.most_common(1)[0][0]
            row = dict(tag=tag, hand=s, object=o, start=a, end=b, R_share=share,
                       R_label=top(stR), R_stages=[(x[0], a + x[1], a + x[2]) for x in stR],
                       H_label=top(stH), H_stages=[(x[0], a + x[1], a + x[2]) for x in stH],
                       R_H_frame_agree=round(float(np.mean([x == y for x, y in zip(labR, labH)])), 2),
                       H_thumb_and_finger_frac=round(float(both.mean()), 2),
                       H_opp_angle_p50=round(float(np.median(oa[both])), 0) if both.any() else None,
                       H_opp_ge110_frac=round(float((oa[both] >= OPP).mean()), 2) if both.any() else None)
            noise = {}
            for sg in SIGMAS:
                fa, ha, nst = [], [], []
                for seed in range(SEEDS):
                    rng = np.random.default_rng(1000 * seed + int(sg * 1000))
                    J = d[f'J_{s}'] + ar1(d['T'], sg, 5.0, rng)[:, None] + rng.normal(0, 0.005, d[f'J_{s}'].shape)
                    lab = [frame_H(J[f], s, d, j, f, surf[o]) for f in fr]
                    st = stages(mode_filter(lab))
                    fa.append(np.mean([x == y for x, y in zip(lab, labH)])); ha.append(top(st) == row['H_label']); nst.append(len(st))
                noise[f'{int(sg * 100)}cm'] = dict(frame_agree=round(float(np.mean(fa)), 2), hold_label_agree=round(float(np.mean(ha)), 2),
                                                   n_stages_mean=round(float(np.mean(nst)), 1))
            row['H_noise'] = noise
            res.append(row)
            print(json.dumps(row), flush=True)
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
