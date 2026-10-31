import sys, os
from huggingface_hub import hf_hub_download
out = sys.argv[1]
files = [
 "runs/20261026-fr32s46b-5e0e100/refs/glockt/ep32/processed/sequence_id=t3_ep032/robot_name=sharpa_wave/ref_gl_ilc.parquet",
 "runs/20261026-fr3233s43-6a8a0e2/refs/glockt/ep33/processed/sequence_id=t3_ep033/robot_name=sharpa_wave/ref_gl_ilc.parquet",
 "runs/20261024-pack-31ef267/refs/glockt/ep16/processed/sequence_id=t3_ep016/robot_name=sharpa_wave/ref_gl_ilc.parquet",
 "runs/20261026-fr32s46b-5e0e100/refs/sf/ep32/assets/mesh/blue_cup/blue_cup.glb",
 "runs/20261026-fr32s46b-5e0e100/refs/sf/ep32/assets/mesh/wooden_spoon/wooden_spoon.glb",
 "runs/20261026-fr32s46b-5e0e100/refs/sf/ep32/assets/urdf/blue_cup_rigid.urdf",
 "runs/20261026-fr32s46b-5e0e100/refs/sf/ep32/assets/urdf/wooden_spoon_rigid.urdf",
 "runs/20261024-pack-31ef267/refs/sf/ep16/assets/mesh/plastic_dish_rack/plastic_dish_rack.glb",
 "runs/20261024-pack-31ef267/refs/sf/ep16/assets/urdf/plastic_dish_rack_rigid.urdf",
 "runs/20261024-pack-31ef267/refs/sf/ep16/assets/urdf/wooden_spoon_rigid.urdf",
 "runs/20261024-pack-31ef267/refs/sf/ep16/assets/mesh/wooden_spoon/wooden_spoon.glb",
]
for f in files:
    try:
        p = hf_hub_download("aebatirel/v2d-store", f, repo_type="dataset", local_dir=out)
        print("OK", p)
    except Exception as e:
        print("FAIL", f, type(e).__name__, str(e)[:200])
