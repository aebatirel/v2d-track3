#!/usr/bin/env python3
"""GT-free identity check of look-alike object pairs along a whole episode (31 Oct 2026). Inference side only.

Inputs: the ego_cam_c video, the camera calibration, our poses (perception poses.npz, or our FlashCHORD reference
under refs/<variant>/ + table_frame.npz + the perception poses.npz for world_T_cam), our meshes. No GT.
  boards  knob rule of pipeline/identity_fix.py (unchanged scoring: mean grey of the camera-facing knob vertices minus
          that of the plate; darker = lower = better), but on every STEP-th frame of the episode instead of frames
          0-6. Per frame: s_as = score(as tracked, no flip) and s_sw = score(swapped, no flip), each summed over the
          two boards; also the best over the 16 flip pairs for each assignment.
  cups    colour: per frame, for each cup, the median (B - R) and HSV saturation over the pixels inside its projected
          convex silhouette (vertices projected, convex hull filled), minus the other cup's silhouette.
          blue_cup should read blue (B - R > 0), beige_cup not. NOTE: ego_cam_c is monochrome (B - R = -1 on every
          public frame), so the usable cue is the median grey level: the blue cup images darker than the beige cup.
Usage: python3 identity.py MODE VIDEO CALIB OUT.json --poses poses.npz [--ref REF.parquet --table table_frame.npz]
       --meshes DIR [--step 5]"""
import argparse
import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import screen  # noqa: E402  (load_perc, load_ref, refine guard)

FL = {'I': np.eye(4), 'Rx': np.diag([1., -1, -1, 1]), 'Ry': np.diag([-1., 1, -1, 1]), 'Rz': np.diag([-1., -1, 1, 1])}


def rect_maps(calib):
    import cv2
    C = json.load(open(calib)); cam = C['cameras']; sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    E = np.array(sp['left_to_right'], float); SZ, RSZ = (1280, 800), (1600, 1000)
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), SZ,
                                                E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(), alpha=0, newImageSize=RSZ,
                                                flags=cv2.CALIB_ZERO_DISPARITY)
    MC = cv2.initUndistortRectifyMap(K_('ego_cam_c'), D_('ego_cam_c'), R1, P1, RSZ, cv2.CV_32FC1)
    return MC, P1[:3, :3]


def frames(video, want, MC):
    import cv2
    cap = cv2.VideoCapture(video); i = 0; out = {}
    while True:
        ok, f = cap.read()
        if not ok or i > max(want):
            break
        if i in want:
            out[i] = cv2.remap(f, MC[0], MC[1], cv2.INTER_LINEAR)
        i += 1
    return out


def cam_poses(a):
    import pyarrow.parquet as pq  # noqa: F401
    P = np.load(screen.refine.checked(a.poses), allow_pickle=False)
    W = np.asarray(P['world_T_cam'], float)
    if a.ref:
        Z = np.load(screen.refine.checked(a.table), allow_pickle=False)
        names, O = screen.load_ref(a.ref, np.asarray(Z['T_table_from_world'], float))
    else:
        names, O = screen.load_perc(a.poses)
    Winv = np.linalg.inv(W)
    return names, np.einsum('tij,tbjk->tbik', Winv, O)  # (T,B,4,4) object -> rectified camera t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode'); ap.add_argument('video'); ap.add_argument('calib'); ap.add_argument('out')
    ap.add_argument('--poses', required=True); ap.add_argument('--ref'); ap.add_argument('--table')
    ap.add_argument('--meshes', required=True); ap.add_argument('--step', type=int, default=5)
    a = ap.parse_args()
    import cv2
    import trimesh
    names, C = cam_poses(a)
    T = len(C)
    MC, KR = rect_maps(a.calib)
    want = list(range(0, T, a.step))
    imgs = frames(a.video, set(want), MC)
    res = dict(mode=a.mode, names=names, T=T, step=a.step, inputs=dict(video=a.video, poses=a.poses, ref=a.ref,
                                                                         table=a.table, meshes=a.meshes), frames=[])
    if a.mode == 'boards':
        NAMES = ['wooden_piece_1', 'wooden_piece_2']
        idx = [names.index(n) for n in NAMES]
        M = {}
        for n in NAMES:
            V = np.asarray(trimesh.load(os.path.join(a.meshes, f'{n}.glb'), force='mesh').vertices); xm = np.median(V[:, 0])
            M[n] = (V[np.abs(V[:, 0] - xm) > 0.009], V[np.abs(V[:, 0] - xm) < 0.003], xm)

        def score(mesh, Tm, img):
            knobs, plate, xm = M[mesh]
            cam_side = np.sign((np.linalg.inv(Tm) @ np.r_[0, 0, 0, 1.0])[0] - xm)
            k = knobs[np.sign(knobs[:, 0] - xm) == cam_side]
            if len(k) < 5:
                return 0.0

            def sample(X):
                Y = X @ Tm[:3, :3].T + Tm[:3, 3]; u = Y @ KR.T; uv = np.round(u[:, :2] / u[:, 2:3]).astype(int)
                ok = (uv[:, 0] >= 0) & (uv[:, 0] < img.shape[1]) & (uv[:, 1] >= 0) & (uv[:, 1] < img.shape[0]) & (Y[:, 2] > 0)
                return img[uv[ok, 1], uv[ok, 0]]
            s_k, s_p = sample(k), sample(plate)
            return float(s_k.mean() - s_p.mean()) if len(s_k) and len(s_p) else 0.0

        for t in want:
            if t not in imgs:
                continue
            g = cv2.GaussianBlur(cv2.cvtColor(imgs[t], cv2.COLOR_BGR2GRAY), (3, 3), 0).astype(float)
            TT = {n: C[t, i] for n, i in zip(NAMES, idx)}
            sc = {}
            for assign in ('as', 'sw'):
                src = dict(zip(NAMES, NAMES if assign == 'as' else NAMES[::-1]))
                vals = {}
                for f1, f2 in itertools.product(FL, FL):
                    vals[(f1, f2)] = score(NAMES[0], TT[src[NAMES[0]]] @ FL[f1], g) + score(NAMES[1], TT[src[NAMES[1]]] @ FL[f2], g)
                sc[assign] = vals
            per = {f'{n}_at_{m}': round(score(n, TT[m], g), 2) for n in NAMES for m in NAMES}  # mesh n at track m
            res['frames'].append(dict(t=t, per_board=per, s_as=round(sc['as'][('I', 'I')], 2), s_sw=round(sc['sw'][('I', 'I')], 2),
                                      best_as=round(min(sc['as'].values()), 2), best_sw=round(min(sc['sw'].values()), 2)))
        F = res['frames']
        d = np.array([f['s_sw'] - f['s_as'] for f in F])
        res['summary'] = dict(n=len(F), share_swap_better=float((d < 0).mean()), median_sw_minus_as=float(np.median(d)),
                              share_swap_better_by5=float((d < -5).mean()), share_as_better_by5=float((d > 5).mean()))
    elif a.mode == 'cups':
        cups = [n for n in names if n in ('blue_cup', 'beige_cup')]
        V = {n: np.asarray(trimesh.load(os.path.join(a.meshes, f'{n}.glb'), force='mesh').vertices) for n in cups}
        for t in want:
            if t not in imgs:
                continue
            img = imgs[t]; hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            masks = {}
            for n in cups:
                Tm = C[t, names.index(n)]
                Y = V[n] @ Tm[:3, :3].T + Tm[:3, 3]
                if (Y[:, 2] <= 0.05).any():
                    continue
                u = Y @ KR.T; uv = (u[:, :2] / u[:, 2:3]).astype(np.int32)
                m = np.zeros(img.shape[:2], np.uint8)
                cv2.fillConvexPoly(m, cv2.convexHull(uv), 1)
                masks[n] = (m > 0, float(Y[:, 2].mean()))
            row = dict(t=t)
            for n in masks:
                m = masks[n][0].copy()
                for o in masks:  # remove the nearer other cup's silhouette
                    if o != n and masks[o][1] < masks[n][1]:
                        m &= ~masks[o][0]
                m = cv2.erode(m.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
                if m.sum() < 200:
                    continue
                px = img[m].astype(float)
                row[n] = dict(px=int(m.sum()), b_minus_r=round(float(np.median(px[:, 0] - px[:, 2])), 1),
                              sat=round(float(np.median(hsv[m][:, 1])), 1), grey=round(float(np.median(px.mean(1))), 1))
            res['frames'].append(row)
        res['summary'] = {}
        for n in cups:
            v = np.array([f[n]['b_minus_r'] for f in res['frames'] if n in f])
            gv = np.array([f[n]['grey'] for f in res['frames'] if n in f])
            res['summary'][n] = dict(n=int(len(v)), grey_p10=float(np.percentile(gv, 10)) if len(gv) else None,
                                     grey_p50=float(np.median(gv)) if len(gv) else None,
                                     grey_p90=float(np.percentile(gv, 90)) if len(gv) else None,
                                     b_minus_r_p10=float(np.percentile(v, 10)) if len(v) else None,
                                     b_minus_r_p50=float(np.median(v)) if len(v) else None,
                                     share_blue_gt20=float((v > 20).mean()) if len(v) else None)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps(res.get('summary')))


if __name__ == '__main__':
    main()
