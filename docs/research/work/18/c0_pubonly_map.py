"""DIG 18 stage B0: PUBLIC-ONLY room map (DIG 18 C0). Same features/matches as run1 (copied db), same mapper options as a2 step_map,
but the incremental mapper is restricted to images that EXCLUDE every frame of the test sessions except their frame 0
(mimics eval: only frame 0 of an eval clip is in the map).
usage: python c0_pubonly_map.py <outdir> [threads]"""
import sys, os, shutil, time, glob
import pycolmap

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1]); NT = int(sys.argv[2]) if len(sys.argv) > 2 else 6
os.makedirs(f"{OUT}/sparse", exist_ok=True)
DB = f"{OUT}/db.db"
if not os.path.exists(DB):
    shutil.copy(f"{HERE}/run1/db.db", DB)
names = []
for c in "abc":
    for p in sorted(glob.glob(f"{HERE}/imgs/{c}/*.jpg")):
        b = os.path.basename(p); tag, fr = b.split("_")[0], int(b.split("_")[1][:4])
        if tag[0] == "e":  # no eval image at all (policy-safe variant: no pooled eval frames)
            continue
        names.append(f"{c}/{b}")
print(time.strftime("%H:%M:%S"), "images kept", len(names), flush=True)
o = pycolmap.IncrementalPipelineOptions()
o.ba_refine_focal_length = False; o.ba_refine_principal_point = False; o.ba_refine_extra_params = False
o.ba_refine_sensor_from_rig = False; o.num_threads = NT; o.random_seed = 0
o.mapper.abs_pose_refine_focal_length = False; o.mapper.abs_pose_refine_extra_params = False
o.mapper.init_min_tri_angle = 6.0; o.multiple_models = True; o.min_model_size = 5
o.image_names = names
recs = pycolmap.incremental_mapping(DB, f"{HERE}/imgs", f"{OUT}/sparse", options=o)
for k, r in recs.items():
    print(time.strftime("%H:%M:%S"), "model", k, r.summary().replace("\n", " | "), flush=True)
print(time.strftime("%H:%M:%S"), "done", flush=True)
