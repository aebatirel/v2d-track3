"""DIG 18 stage A2: room SfM with pycolmap (CPU). Steps are resumable (each skips when its output exists).
  feat  : SIFT per camera folder (PINHOLE, fixed intrinsics of the undistorted images), masks from a1.
  rig   : ego mono pair as a rig: c = reference sensor, b = c->b factory extrinsic (stereo_pairs ego left_to_right,
          X_b = R X_c + t, t_x = -7.55 cm) -> metric scale. cam_a is a separate single-camera rig (sync with b/c is not
          assumed; checked afterwards).
  pairs : within-episode all pairs + cross-episode random pairs + all frame-0 pairs.
  match : SIFT matching + geometric verification on the pair list.
  map   : incremental mapping, intrinsics and rig extrinsics fixed.
usage: python a2_sfm.py <outdir> <steps csv> [maxfeat] [ncross]"""
import sys, os, json, glob, random, time, numpy as np
import pycolmap

ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1]); STEPS = sys.argv[2].split(",")
MAXF = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
NCROSS = int(sys.argv[4]) if len(sys.argv) > 4 else 12
IMG = f"{HERE}/imgs"; MSK = f"{HERE}/masks"; DB = f"{OUT}/db.db"
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, HERE)
from a1_extract import NEW
CAL = json.load(open(f"{ROOT}/data/track_3/public/meta/camera_calibration.json"))
EGO = [s for s in CAL["stereo_pairs"] if s["camera"] == "ego"][0]
assert EGO["left"] == "ego_cam_c" and EGO["right"] == "ego_cam_b"
T_bc = np.array(EGO["left_to_right"], float)  # X_b = R X_c + t


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def names(c):
    return sorted(f"{c}/{os.path.basename(p)}" for p in glob.glob(f"{IMG}/{c}/*.jpg"))


def step_feat():
    if os.path.exists(DB):
        log("feat: db exists, skip"); return
    for c in "abc":
        w, h, f = NEW[c]
        ro = pycolmap.ImageReaderOptions()
        ro.camera_model = "PINHOLE"; ro.camera_params = f"{f},{f},{(w - 1) / 2},{(h - 1) / 2}"; ro.mask_path = MSK
        eo = pycolmap.FeatureExtractionOptions(); eo.sift.max_num_features = MAXF; eo.num_threads = 12
        pycolmap.extract_features(DB, IMG, image_names=names(c), camera_mode=pycolmap.CameraMode.SINGLE,
                                  reader_options=ro, extraction_options=eo, device=pycolmap.Device.cpu)
        log("feat", c, len(names(c)))


def step_rig():
    db = pycolmap.Database.open(DB)
    cams = {}
    for im in db.read_all_images():
        cams.setdefault(im.name.split("/")[0], set()).add(im.camera_id)
    log("cameras per folder", {k: sorted(v) for k, v in cams.items()})
    rc = [pycolmap.RigConfig(cameras=[
              pycolmap.RigConfigCamera(ref_sensor=True, image_prefix="c/"),
              pycolmap.RigConfigCamera(image_prefix="b/", cam_from_rig=pycolmap.Rigid3d(T_bc[:3, :]))]),
          pycolmap.RigConfig(cameras=[pycolmap.RigConfigCamera(ref_sensor=True, image_prefix="a/")])]
    pycolmap.apply_rig_config(rc, db)
    log("rigs", db.num_rigs(), "frames", db.num_frames(), "images", db.num_images())
    db.close()


def step_pairs():
    fn = f"{OUT}/pairs.txt"
    if os.path.exists(fn):
        log("pairs exist, skip"); return
    allim = names("a") + names("b") + names("c")
    ep = {n: n.split("/")[1].split("_")[0] for n in allim}
    fr = {n: int(n.split("_")[1].split(".")[0]) for n in allim}
    rng = random.Random(0); P = set()
    def add(x, y):
        if x != y: P.add(tuple(sorted((x, y))))
    by = {}
    for n in allim: by.setdefault(ep[n], []).append(n)
    for e, L in by.items():  # within episode, all pairs
        for i in range(len(L)):
            for j in range(i + 1, len(L)): add(L[i], L[j])
    f0 = [n for n in allim if fr[n] == 0]
    for i in range(len(f0)):  # all frame-0 images (public + eval), all cams
        for j in range(i + 1, len(f0)): add(f0[i], f0[j])
    for n in allim:  # cross-episode random
        others = [m for m in allim if ep[m] != ep[n]]
        for m in rng.sample(others, NCROSS): add(n, m)
    with open(fn, "w") as f:
        for x, y in sorted(P): f.write(f"{x} {y}\n")
    log("pairs", len(P))


def step_match():
    db = pycolmap.Database.open(DB); n = db.num_matched_image_pairs(); db.close()
    if n > 0:
        log("match: already", n, "pairs, skip"); return
    mo = pycolmap.FeatureMatchingOptions(); mo.num_threads = 12
    po = pycolmap.ImportedPairingOptions(); po.match_list_path = f"{OUT}/pairs.txt"
    vo = pycolmap.TwoViewGeometryOptions()
    pycolmap.match_image_pairs(DB, matching_options=mo, pairing_options=po, verification_options=vo,
                               device=pycolmap.Device.cpu)
    db = pycolmap.Database.open(DB); log("matched pairs", db.num_matched_image_pairs(), "verified",
                                         db.num_verified_image_pairs()); db.close()


def step_map():
    o = pycolmap.IncrementalPipelineOptions()
    o.ba_refine_focal_length = False; o.ba_refine_principal_point = False; o.ba_refine_extra_params = False
    o.ba_refine_sensor_from_rig = False; o.num_threads = 12; o.random_seed = 0
    o.mapper.abs_pose_refine_focal_length = False; o.mapper.abs_pose_refine_extra_params = False
    o.mapper.init_min_tri_angle = 6.0; o.multiple_models = True; o.min_model_size = 5
    os.makedirs(f"{OUT}/sparse", exist_ok=True)
    recs = pycolmap.incremental_mapping(DB, IMG, f"{OUT}/sparse", options=o)
    for k, r in recs.items():
        log("model", k, r.summary().replace("\n", " | "))


for s in STEPS:
    log("== step", s); globals()[f"step_{s}"]()
log("done")
