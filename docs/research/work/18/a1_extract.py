"""DIG 18 stage A1: extract + undistort frames for the room SfM map.
Each sampled frame index of a clip is written for cams a/b/c into imgs/{a,b,c}/<tag>_<frame>.jpg as an
undistorted PINHOLE image (calibration AS GIVEN, stored frames upright, never rotated). The undistortion keeps the
camera orientation (R=None), so a pose fitted for the raw camera holds for the undistorted one.
cam_a is halved (1014x760) before use. Masks (COLMAP convention: 0 = no features) cover the bottom-centre
table/hands/objects region roughly.
usage: python a1_extract.py <step> <public eps csv|all> <eval eps csv|all|none> [preview]"""
import sys, os, json, numpy as np, cv2

ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
D3 = f"{ROOT}/data/track_3"
OUT = os.path.dirname(os.path.abspath(__file__))
CAL = json.load(open(f"{D3}/public/meta/camera_calibration.json"))["cameras"]
PUB = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44]
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
# new pinhole cameras (width, height, f)
NEW = {"a": (1014, 760, 500.0), "b": (1280, 800, 420.0), "c": (1280, 800, 420.0)}


def newK(c):
    w, h, f = NEW[c]
    return np.array([[f, 0, (w - 1) / 2], [0, f, (h - 1) / 2], [0, 0, 1.0]])


def maps(c):
    cal = CAL[f"ego_cam_{c}"]
    K = np.array(cal["intrinsic_matrix"], float); d = np.array(cal["distortion_coefficients"], float)
    w0, h0 = cal["resolution"]
    w, h, f = NEW[c]
    return cv2.initUndistortRectifyMap(K, d, None, newK(c), (w, h), cv2.CV_32FC1), (w0, h0)


def mask(c):
    """255 = use. Bottom-centre region (table, objects, hands, own body) excluded."""
    w, h, f = NEW[c]
    m = np.full((h, w), 255, np.uint8)
    # in normalised coords y = (v-cy)/f; exclude below y > 0.30 in the central band |x| < 0.85, and y > 0.55 anywhere
    u, v = np.meshgrid(np.arange(w), np.arange(h))
    x = (u - (w - 1) / 2) / f; y = (v - (h - 1) / 2) / f
    if c == "a": bad = ((y > 0.20) & (np.abs(x) < 0.90)) | (y > 0.42)
    else: bad = ((y > 0.30) & (np.abs(x) < 0.90)) | (y > 0.55)
    m[bad] = 0
    return m


def clip(split, ep, c):
    return f"{D3}/{split}/videos/chunk-000/observation.images.ego_cam_{c}/episode_{ep:06d}.mp4"


def run(step, pubs, evs, preview=False):
    M = {c: maps(c) for c in "abc"}
    for c in "abc":
        os.makedirs(f"{OUT}/imgs/{c}", exist_ok=True); os.makedirs(f"{OUT}/masks/{c}", exist_ok=True)
    MK = {c: mask(c) for c in "abc"}
    jobs = [("public", e, "p") for e in pubs] + [("evaluation", e, "e") for e in evs]
    for split, ep, pre in jobs:
        tag = f"{pre}{ep:02d}"
        paths = {c: clip(split, ep, c) for c in "abc"}
        if not all(os.path.exists(p) for p in paths.values()):
            print(tag, "missing clip(s)", [c for c, p in paths.items() if not os.path.exists(p)], flush=True)
        for c, p in paths.items():
            if not os.path.exists(p): continue
            cap = cv2.VideoCapture(p); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            want = set([0]) if split == "evaluation" else set(range(0, n, step))
            (m1, m2), (w0, h0) = M[c]; i = 0
            while i <= max(want):
                ok, fr = cap.read()
                if not ok: break
                if i in want:
                    assert fr.shape[1] == w0 and fr.shape[0] == h0, (fr.shape, w0, h0)
                    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if c != "a" else fr
                    u = cv2.remap(g, m1, m2, cv2.INTER_AREA if c == "a" else cv2.INTER_LINEAR)
                    name = f"{tag}_{i:04d}.jpg"
                    cv2.imwrite(f"{OUT}/imgs/{c}/{name}", u, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    cv2.imwrite(f"{OUT}/masks/{c}/{name}.png", MK[c])
                    if preview:
                        vis = u.copy() if u.ndim == 3 else cv2.cvtColor(u, cv2.COLOR_GRAY2BGR)
                        vis[MK[c] == 0] = (vis[MK[c] == 0] * 0.4).astype(np.uint8)
                        cv2.imwrite(f"{OUT}/preview_{c}_{name}", cv2.resize(vis, (vis.shape[1] // 2, vis.shape[0] // 2)))
                i += 1
        print(tag, "done", flush=True)


if __name__ == "__main__":
    step = int(sys.argv[1])
    pubs = PUB if sys.argv[2] == "all" else ([] if sys.argv[2] == "none" else [int(x) for x in sys.argv[2].split(",")])
    evs = EV if sys.argv[3] == "all" else ([] if sys.argv[3] == "none" else [int(x) for x in sys.argv[3].split(",")])
    run(step, pubs, evs, preview=len(sys.argv) > 4)
