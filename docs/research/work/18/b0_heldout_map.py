"""DIG 18 stage B0: held-out room map. Same features/matches as run1 (copied db), same mapper options as a2 step_map,
but the incremental mapper is restricted to images that EXCLUDE every frame of the test sessions except their frame 0
(mimics eval: only frame 0 of an eval clip is in the map).
usage: python b0_heldout_map.py <outdir> <test public eps csv>"""
import sys, os, shutil, time, glob
import pycolmap

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1]); TEST = [int(x) for x in sys.argv[2].split(",")]
os.makedirs(f"{OUT}/sparse", exist_ok=True)
DB = f"{OUT}/db.db"
if not os.path.exists(DB):
    shutil.copy(f"{HERE}/run1/db.db", DB)
names = []
for c in "abc":
    for p in sorted(glob.glob(f"{HERE}/imgs/{c}/*.jpg")):
        b = os.path.basename(p); tag, fr = b.split("_")[0], int(b.split("_")[1][:4])
        if tag[0] == "p" and int(tag[1:]) in TEST and fr != 0:
            continue
        names.append(f"{c}/{b}")
print(time.strftime("%H:%M:%S"), "images kept", len(names), flush=True)
o = pycolmap.IncrementalPipelineOptions()
o.ba_refine_focal_length = False; o.ba_refine_principal_point = False; o.ba_refine_extra_params = False
o.ba_refine_sensor_from_rig = False; o.num_threads = 10; o.random_seed = 0
o.mapper.abs_pose_refine_focal_length = False; o.mapper.abs_pose_refine_extra_params = False
o.mapper.init_min_tri_angle = 6.0; o.multiple_models = True; o.min_model_size = 5
o.image_names = names
recs = pycolmap.incremental_mapping(DB, f"{HERE}/imgs", f"{OUT}/sparse", options=o)
for k, r in recs.items():
    print(time.strftime("%H:%M:%S"), "model", k, r.summary().replace("\n", " | "), flush=True)
print(time.strftime("%H:%M:%S"), "done", flush=True)
