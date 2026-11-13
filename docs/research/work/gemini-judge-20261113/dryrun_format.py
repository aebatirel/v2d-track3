#!/usr/bin/env python3
"""Format dry run (allowed before the PREREG commit): ONE Decisions API request on NON-challenge images only.

Builds two synthetic pictures from trimesh primitives with the same code and layout as the real tests:
  - G-A layout: left half a shaded render of a primitive "mug" (cylinder + torus handle) on a noise background, right
    half a grey render of a different primitive (a plain cylinder), 1030 x 512, as ga_build.py makes its pairs;
  - G-B layout: a primitive box on a noise background, left clean, right with a magenta outline of the box shifted by
    a few pixels, 902 x 448, as gb_build.py makes its composites.
Sends one request with both pictures (resolution high) and BOTH exact question texts from questions.json (the G-A
score question and the G-B noul question), through run_gemini.build_body / run_gemini.post (the runner's own code
path; no key handling). Writes the request (images as path + sha256) and the full response to --out. The answers are
meaningless; the purpose is the request format, the answer format and the token count per image and per text.
Usage: dryrun_format.py --questions questions.json --out DIR [--no_send]
"""
import argparse, hashlib, json, os, sys, time

import numpy as np
import cv2
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gj_common as C  # noqa: E402
import run_gemini as RG  # noqa: E402


def pinhole_rays(K, out):
    g = np.arange(out) + 0.5
    u, v = np.meshgrid(g, g)
    d = np.stack([(u - K[0, 2]) / K[0, 0], (v - K[1, 2]) / K[1, 1], np.ones_like(u)], -1)
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--questions', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--no_send', action='store_true', help='write the two pictures and stop (no network)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    Q = json.load(open(a.questions))
    rng = np.random.default_rng(0)
    K = np.array([[700.0, 0, 256], [0, 700.0, 256], [0, 0, 1]])
    T = np.eye(4); T[:3, :3] = cv2.Rodrigues(np.array([-1.1, 0.0, 0.3]))[0]; T[:3, 3] = [0, 0.0, 0.45]
    rays = pinhole_rays(K, 512)
    mug = trimesh.util.concatenate([trimesh.creation.cylinder(radius=0.04, height=0.10, sections=64),
                                    trimesh.creation.torus(0.025, 0.007).apply_transform(
                                        trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
                                    .apply_translation([0.045, 0, 0])])
    cyl = trimesh.creation.cylinder(radius=0.04, height=0.10, sections=64)
    bg = (rng.integers(90, 160, (512, 512, 1)) * np.ones((1, 1, 3))).astype(np.uint8)
    r1, h1 = C.Shader(np.asarray(mug.vertices), np.asarray(mug.faces)).render(T, rays)
    left = bg.copy(); left[h1] = np.stack([r1[h1] * 0.5, r1[h1] * 0.6, r1[h1] * 1.0], -1).clip(0, 255).astype(np.uint8)
    r2, _ = C.Shader(np.asarray(cyl.vertices), np.asarray(cyl.faces)).render(T, rays)
    pair = np.full((512, 1030, 3), 128, np.uint8); pair[:, :512] = left; pair[:, 518:] = r2[..., None]
    box = trimesh.creation.box([0.08, 0.05, 0.03])
    rays448 = pinhole_rays(np.array([[600.0, 0, 224], [0, 600.0, 224], [0, 0, 1]]), 448)
    T2 = np.eye(4); T2[:3, :3] = cv2.Rodrigues(np.array([-0.9, 0.2, 0.4]))[0]; T2[:3, 3] = [0, 0, 0.4]
    r3, h3 = C.Shader(np.asarray(box.vertices), np.asarray(box.faces)).render(T2, rays448)
    scene = (rng.integers(60, 120, (448, 448, 1)) * np.ones((1, 1, 3))).astype(np.uint8)
    scene[h3] = np.stack([r3[h3]] * 3, -1)
    T2s = T2.copy(); T2s[:3, 3] += [0.008, 0.004, 0]
    m = C.silhouette_pinhole(np.asarray(box.vertices), np.asarray(box.faces), T2s,
                             np.array([[600.0, 0, 224], [0, 600.0, 224], [0, 0, 1]]), 224, 224, 448, 448)
    over = scene.copy(); cv2.drawContours(over, C.outline(m), -1, (255, 0, 255), 2, cv2.LINE_AA)
    comp = np.full((448, 902, 3), 128, np.uint8); comp[:, :448] = scene; comp[:, 454:] = over
    paths = []
    for name, img in (('dry_GA_pair.jpg', pair), ('dry_GB_comp.jpg', comp)):
        p = os.path.join(a.out, name); open(p, 'wb').write(C.jpeg_bytes(img, 90)); paths.append(p)
    GA, GB = Q['GA'], Q['GB']
    spec = dict(id='dryrun-format-1', input=[
        dict(type='text', text=GA['input_intro'].format(name='toy mug', n=1)),
        dict(type='text', text=GA['input_view'].format(i=1)),
        dict(type='image', path=paths[0], mime_type='image/jpeg', resolution='high',
             sha256=hashlib.sha256(open(paths[0], 'rb').read()).hexdigest()),
        dict(type='text', text=GB['input_intro'].format(name='toy box')),
        dict(type='image', path=paths[1], mime_type='image/jpeg', resolution='high',
             sha256=hashlib.sha256(open(paths[1], 'rb').read()).hexdigest())],
        questions={**GA['questions'], **GB['questions']})
    body, keep = RG.build_body(spec)
    if a.no_send:
        print('pictures written, nothing sent:', paths); return
    chars = dict(text_input=sum(len(b['text']) for b in spec['input'] if b['type'] == 'text'),
                 questions_GA=len(json.dumps(GA['questions'])), questions_GB=len(json.dumps(GB['questions'])))
    t0 = time.time(); ts = RG.now()
    status, text = RG.post(body, 60)
    dt = time.time() - t0
    try:
        resp = json.loads(text)
    except Exception:
        resp = text
    rec = dict(t_start=ts, latency_s=round(dt, 3), http_status=status, request=keep, chars=chars, response=resp)
    json.dump(rec, open(os.path.join(a.out, 'dryrun_format.json'), 'w'), indent=1)
    print(json.dumps(dict(http_status=status, latency_s=round(dt, 3), chars=chars,
                          usage=resp.get('usage') if isinstance(resp, dict) else None,
                          answers=resp.get('answers') if isinstance(resp, dict) else resp), indent=1))


if __name__ == '__main__':
    main()
