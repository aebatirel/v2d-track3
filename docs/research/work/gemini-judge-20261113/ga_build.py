#!/usr/bin/env python3
"""Test G-A inputs (Gemini mesh selector, note 28 idea 2): one Decisions API request per scored mesh of the 30 Oct
generative probe (104 meshes). INFERENCE SIDE ONLY: our tracks, our hands, the public calibration and colour video,
our library_v3 mesh and the candidate meshes. No scan, no mocap, no parquet, no CD-O (the scoring set list
score_manifest.tsv holds labels and paths only).

Per object (10 objects; each mesh is judged on its object's frames, identical for all candidates of that object):
  1. Candidate frames k of the object's probe episode (the same tracks the probe used: store run
     20261025-sweep-a894083, results/sweep/base/ep<N>/poses.npz; hands runs/20261025-g1-022fece/refs/perc2m):
       - our library_v3 silhouette at the tracked pose fully inside the colour image (margin 20 px);
       - occlusion by the episode's other tracked objects <= 10 % (z-buffer of library meshes);
       - MediaPipe hand cover of the visible silhouette <= 25 % (bones drawn 0.22 x the wrist-to-middle-MCP length);
       - track speed (world, median over 7 frames) <= 8 mm per frame (motion blur);
       - visible silhouette >= 4,000 px;
       - track check (GT-free, added after a library-overlay check showed the ep23 wooden_piece_1 track lost from
         about frame 141 on): edge support = share of our library_v3 silhouette outline within 4 px of a Canny edge of
         the colour frame (Gaussian 5 px, thresholds 40/100), median over frames k-3..k+3; usable only if it is at
         least EDGE_REL = 0.5 x the median edge support of the seed frames (where the generators' crops were made).
  2. Viewing direction of each frame in the object frame. The frames the generators were conditioned on (crop k of
     each single-image label, Pixal3D view k from views/<ep_obj>/probe_meta.json) are seeds. N_VIEWS = 4 frames are
     chosen by seeded farthest-point sampling on the direction sphere (largest minimum angle to the seeds and to the
     frames already chosen; among candidates within 2 degrees of the best, the largest visible silhouette; frames
     >= 10 apart). So the judge sees mostly sides the generators did not see.
  3. Window per frame: square around the library_v3 silhouette (1.4 x its longest edge, at least 160 px).
Per mesh and frame: the real colour crop (frame j = k + a_offset) and a ray-cast grey render of the candidate at our
tracked pose in the same distorted colour camera and the same window, both 512 x 512, side by side (1030 x 512 JPEG,
6 px grey separator). One request per mesh: intro text, then 4 x ("Picture i:" + image, resolution high), one score
question (questions.json GA).

Usage: ga_build.py --manifest score_manifest.tsv --views VIEWS_DIR --mesh_root DIR --tracks DIR --videos DIR
                   --calib camera_calibration.json --lib meshes/library_v3 --questions questions.json --out OUT
"""
import argparse, hashlib, json, os, sys, time

import numpy as np
import cv2
import trimesh
from scipy.ndimage import median_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gj_common as C  # noqa: E402

EP = dict(white_pot=41, white_pot_lid=2, blue_cup=22, water_pitcher=22, wooden_piece_1=23, wooden_piece_2=23,
          plastic_dish_rack=26, mini_sweeper=31, mini_dust_pan=39, beige_cup=11)      # gen_analysis.py
N_VIEWS, PANEL, SEP = 4, 512, 6
MARGIN, OCCL_MAX, HAND_MAX, SPEED_MAX, VIS_MIN = 20, 0.10, 0.25, 8e-3, 4000
TOL_DEG, MIN_GAP, GROW, MIN_SIDE, EDGE_REL, EDGE_PX = 2.0, 10, 1.4, 160, 0.5, 4
BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12), (9, 13),
         (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]


def render_ids(pts, poses, K, D, W, H, scale=0.5):
    """crops.render_ids: nearest-object id per pixel by splatting surface samples (0 = none)."""
    w, h = int(W * scale), int(H * scale)
    zb = np.full(h * w, np.inf); idb = np.zeros(h * w, np.int32)
    for i, (P, T) in enumerate(zip(pts, poses), 1):
        X = P @ T[:3, :3].T + T[:3, 3]
        X = X[X[:, 2] > 0.05]
        uv = C.project_distorted(X, K, D) * scale
        iu, iv = np.round(uv[:, 0]).astype(int), np.round(uv[:, 1]).astype(int)
        ok = (iu >= 0) & (iu < w) & (iv >= 0) & (iv < h)
        lin = iv[ok] * w + iu[ok]; z = X[ok, 2]
        o = np.argsort(-z); lin, z = lin[o], z[o]
        closer = z < zb[lin]
        zb[lin[closer]] = z[closer]; idb[lin[closer]] = i
    return cv2.resize(idb.reshape(h, w).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)


def hand_mask(Hd, k, W, H):
    m = np.zeros((H, W), np.uint8)
    for side in ('left', 'right'):
        if k >= len(Hd[f'valid_{side}']) or not Hd[f'valid_{side}'][k]:
            continue
        uv = Hd[f'uv_a_{side}'][k]
        if not np.isfinite(uv).all():
            continue
        L = float(np.linalg.norm(uv[9] - uv[0]))
        th = max(int(round(0.22 * L)), 3)
        for a, b in BONES:
            cv2.line(m, tuple(np.round(uv[a]).astype(int)), tuple(np.round(uv[b]).astype(int)), 1, th)
        cv2.fillPoly(m, [np.round(uv[[0, 1, 5, 9, 13, 17]]).astype(np.int32)], 1)
    return m


def edge_support(img, V, F, T, Ka, Da):
    """Share of the library silhouette's outline (exact per-face fill) within EDGE_PX of a Canny edge."""
    H, W = img.shape[:2]
    uv = C.project_distorted(V @ T[:3, :3].T + T[:3, 3], Ka, Da)
    m = np.zeros((H, W), np.uint8)
    for f in np.round(uv[F] * 16).astype(np.int32):
        cv2.fillConvexPoly(m, f, 1, cv2.LINE_8, 4)
    cm = np.zeros_like(m)
    cv2.drawContours(cm, C.outline(m), -1, 1, 1)
    if cm.sum() == 0:
        return np.nan
    e = cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0), 40, 100)
    dt = cv2.distanceTransform((e == 0).astype(np.uint8), cv2.DIST_L2, 3)
    return float((dt[cm > 0] <= EDGE_PX).mean())


def angle(a, b):
    return np.degrees(np.arccos(np.clip(a @ b, -1, 1)))


def select_frames(obj, ep, a, Ka, Da, T_a_rect, lib, seeds_k, log):
    P = np.load(C.guard(os.path.join(a.tracks, f'ep{ep}', 'poses.npz')))
    Hd = np.load(C.guard(os.path.join(a.tracks, f'ep{ep}', 'hands.npz')))
    a_off = int(Hd['a_offset'])
    names = [k[len('cam_T_'):] for k in P.files if k.startswith('cam_T_')]
    order = [obj] + [n for n in names if n != obj]
    pts = [trimesh.sample.sample_surface_even(trimesh.Trimesh(*lib[n], process=False), 60000, seed=0)[0]
           for n in order]
    V0 = lib[obj][0]
    c = 0.5 * (V0.min(0) + V0.max(0))
    T_o, W_C = P['cam_T_' + obj], P['world_T_cam']
    pos = np.stack([(W_C[t] @ T_o[t])[:3, 3] for t in range(len(T_o))])
    speed = median_filter(np.r_[0.0, np.linalg.norm(np.diff(pos, axis=0), axis=1)], size=7, mode='nearest')
    vid = C.Reader(os.path.join(a.videos, f'ep{ep}_a.mp4'))
    W, H = vid.W, vid.H

    def direction(k):
        T = T_o[k].astype(np.float64)
        d = T[:3, :3].T @ (-T[:3, 3]) - c
        return d / np.linalg.norm(d)

    F0 = lib[obj][1]
    edge = np.full(len(T_o), np.nan)
    for k in range(len(T_o)):
        if k + a_off < vid.n:
            img = vid.get(k + a_off)
            if img is not None:
                edge[k] = edge_support(img, V0, F0, T_a_rect @ T_o[k].astype(np.float64), Ka, Da)
    edge_s = np.array([np.nanmedian(edge[max(0, k - 3):k + 4]) for k in range(len(T_o))])
    edge_ref = float(np.nanmedian([edge[k] for k in seeds_k]))
    cands = []
    for k in range(len(T_o)):
        j = k + a_off
        if j >= vid.n:
            continue
        poses = [T_a_rect @ P['cam_T_' + n][k].astype(np.float64) for n in order]
        ids = render_ids(pts, poses, Ka, Da, W, H)
        full = render_ids(pts[:1], poses[:1], Ka, Da, W, H) == 1
        vis = ids == 1
        if full.sum() == 0:
            continue
        ys, xs = np.nonzero(full)
        inside = xs.min() > MARGIN and ys.min() > MARGIN and xs.max() < W - MARGIN and ys.max() < H - MARGIN
        occl = 1 - vis.sum() / full.sum()
        hm = hand_mask(Hd, k, W, H)
        hand = float((vis & (hm > 0)).sum() / max(vis.sum(), 1))
        edge_ok = bool(edge_s[k] >= EDGE_REL * edge_ref)
        ok = bool(inside and occl <= OCCL_MAX and hand <= HAND_MAX and speed[k] <= SPEED_MAX and vis.sum() >= VIS_MIN
                  and edge_ok)
        cands.append(dict(k=k, j=j, vis=int(vis.sum()), occl=round(float(occl), 4), hand=round(hand, 4),
                          speed_mm=round(float(speed[k]) * 1e3, 2), inside=bool(inside),
                          edge=round(float(edge[k]), 3), edge_med7=round(float(edge_s[k]), 3), edge_ok=edge_ok,
                          ok=ok))
    good = [x for x in cands if x['ok']]
    S = [direction(k) for k in seeds_k]
    picked = []
    for _ in range(N_VIEWS):
        best = None
        scored = []
        for x in good:
            if any(abs(x['k'] - p['k']) < MIN_GAP for p in picked):
                continue
            d = direction(x['k'])
            ref = S + [direction(p['k']) for p in picked]
            m = min(angle(d, r) for r in ref) if ref else 180.0
            scored.append((m, x))
        if not scored:
            break
        mbest = max(m for m, _ in scored)
        pool = [(m, x) for m, x in scored if m >= mbest - TOL_DEG]
        m, x = max(pool, key=lambda t: (t[1]['vis'], -t[1]['k']))
        picked.append(dict(x, min_angle_deg=round(float(m), 2)))
    log.update(obj=obj, ep=ep, a_offset=a_off, n_frames=len(T_o), n_candidates=len(cands), n_good=len(good),
               edge_ref=round(edge_ref, 3), edge_threshold=round(EDGE_REL * edge_ref, 3),
               n_fail_edge_only=sum(1 for x in cands if not x['edge_ok'] and x['inside'] and x['occl'] <= OCCL_MAX
                                    and x['hand'] <= HAND_MAX and x['speed_mm'] <= SPEED_MAX * 1e3
                                    and x['vis'] >= VIS_MIN),
               usable_k=[x['k'] for x in good],
               seeds_k=seeds_k, picked=picked,
               seed_dirs_spread_deg=round(float(max([angle(p, q) for p in S for q in S] + [0])), 2))
    return P, a_off, picked


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('manifest', 'views', 'mesh_root', 'tracks', 'videos', 'calib', 'lib', 'questions', 'out'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--only', default=None, help='comma list of objects (testing)')
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(os.path.join(a.out, 'img'), exist_ok=True)
    Q = json.load(open(a.questions))
    GA = Q['GA']
    Ka, Da, T_a_rect = C.colour_geometry(C.guard(a.calib))
    rows = [l.rstrip('\n').split('\t') for l in open(C.guard(a.manifest)) if l.strip()]
    lib = {}
    for f in sorted(os.listdir(a.lib)):
        if f.endswith('.glb'):
            lib[f[:-4]] = C.load_mesh(os.path.join(a.lib, f))
    objs = [o for o in EP if a.only is None or o in a.only.split(',')]
    specs, sel_log = [], {}
    for obj in objs:
        ep = EP[obj]
        mine = [r for r in rows if r[1] == obj]
        seeds = sorted({C.k_from_label(r[0]) for r in mine if C.k_from_label(r[0]) is not None})
        meta = json.load(open(C.guard(os.path.join(a.views, f'ep{ep}_{obj}', 'probe_meta.json'))))
        seeds = sorted(set(seeds) | {int(v['k']) for v in meta['chosen']})
        log = {}
        P, a_off, picked = select_frames(obj, ep, a, Ka, Da, T_a_rect, lib, seeds, log)
        sel_log[obj] = log
        print(f'[ga] {obj} ep{ep}: {log["n_good"]}/{log["n_candidates"]} usable frames, seeds {seeds}, picked '
              f'{[(p["k"], p["min_angle_deg"]) for p in picked]}', flush=True)
        vid = C.Reader(os.path.join(a.videos, f'ep{ep}_a.mp4'))
        V0, F0 = lib[obj]
        views = []
        for i, p in enumerate(picked):
            T = T_a_rect @ P['cam_T_' + obj][p['k']].astype(np.float64)
            X = V0 @ T[:3, :3].T + T[:3, 3]
            uv = C.project_distorted(X, Ka, Da)
            cx, cy, side = C.square_window(*uv.min(0), *uv.max(0), GROW, MIN_SIDE)
            real = C.crop_affine(vid.get(p['j']), cx, cy, side, PANEL)
            rays = C.pixel_rays_distorted(Ka, Da, cx, cy, side, PANEL)
            views.append(dict(k=p['k'], j=p['j'], T=T, window=[round(cx, 2), round(cy, 2), round(side, 2)],
                              real=real, rays=rays))
            cv2.imwrite(os.path.join(a.out, 'img', f'real_{obj}_k{p["k"]}.jpg'), real)
        for r in mine:
            label, path = r[0], r[2]
            local = os.path.join(a.mesh_root, path.split('/results/', 1)[1])
            V, F = C.load_mesh(local)
            sh = C.Shader(V, F)
            blocks = [dict(type='text', text=GA['input_intro'].format(name=C.nice_name(obj), n=len(views)))]
            imgs = []
            for i, v in enumerate(views, 1):
                rend, hit = sh.render(v['T'], v['rays'])
                pair = np.full((PANEL, 2 * PANEL + SEP, 3), 128, np.uint8)
                pair[:, :PANEL] = v['real']; pair[:, PANEL + SEP:] = rend[..., None]
                fn = os.path.join(a.out, 'img', label.replace('/', '__') + f'_v{i}.jpg')
                b = C.jpeg_bytes(pair, 90)
                open(fn, 'wb').write(b)
                blocks.append(dict(type='text', text=GA['input_view'].format(i=i)))
                blocks.append(dict(type='image', path=os.path.abspath(fn), mime_type='image/jpeg',
                                   resolution=GA['image_resolution'], sha256=hashlib.sha256(b).hexdigest()))
                imgs.append(dict(k=v['k'], j=v['j'], window=v['window'], render_hit_px=int(hit.sum())))
            specs.append(dict(id=label, test='GA', object=obj, episode=ep, group=r[3], mesh=local,
                              mesh_faces=int(len(F)), views=imgs, input=blocks, questions=GA['questions']))
            print(f'[ga]   {label}: faces {len(F)}, render px {[x["render_hit_px"] for x in imgs]}', flush=True)
    C.write_jsonl(os.path.join(a.out, 'specs_GA.jsonl'), specs)
    json.dump(dict(params=dict(N_VIEWS=N_VIEWS, PANEL=PANEL, SEP=SEP, MARGIN=MARGIN, OCCL_MAX=OCCL_MAX,
                               HAND_MAX=HAND_MAX, SPEED_MAX=SPEED_MAX, VIS_MIN=VIS_MIN, TOL_DEG=TOL_DEG,
                               MIN_GAP=MIN_GAP, GROW=GROW, MIN_SIDE=MIN_SIDE, EDGE_REL=EDGE_REL, EDGE_PX=EDGE_PX),
                   selection=sel_log, n_specs=len(specs), seconds=round(time.time() - t0, 1)),
              open(os.path.join(a.out, 'frames_GA.json'), 'w'), indent=1, default=float)
    print(f'[ga] wrote {len(specs)} specs in {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
