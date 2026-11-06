"""Masses v2 reference table (31 Oct 2026): refs_v2.json, the per-episode source run, base, pull list (store paths
relative to runs/<source_run>/, single-file downloads on the box, no store listing) and the expected md5 / fingerprint
of each finished grasp-lock reference, for the 4 episodes PREREG.md section 3 selects. Inputs: the 29 Oct store listing
(file names of the 24-25 Oct runs) and the orcB job log (file names of its 30 Oct ep13 reference), plus the reference
files downloaded once each (scratchpad massv2/dl) for md5 / fingerprint / URDF checks. Nothing here reads ground truth.
Usage: python3 make_table.py DL_DIR EP31_GLOCKT_PARQUET OUT.json"""
import glob, hashlib, json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../tools'))
import mass_arm, pyarrow.parquet as pq   # noqa: E402

DL, EP31, OUT = sys.argv[1:4]
H = 'sequence_id=t3_ep{:03d}/robot_name=sharpa_wave'
SRC = {   # episode: (source run, base, base processed parquet name, objects) -- names from the 29 Oct listing / orcB job.log
    24: ('20261024-ev3-2c1e4dd', 'mcs', 'a53cdb5b5f2c4c41987b6e1ff96bba60-0.parquet', ('wooden_piece_1', 'wooden_piece_2')),
    11: ('20261025-twin11v3-0e8aebb', 'mck', 'd6e85c126bb940e0b7c17ebaff9e87d6-0.parquet', ('beige_cup', 'blue_cup')),
    13: ('20261030-orcB-38234d1', 'mck', '0d7b4754b12b4f4aad38b344b3f82c5f-0.parquet', ('blue_cup', 'plastic_dish_rack')),
    31: ('20261024-ev30rp-07eef1a', 'mck', '919152d3c8c943f3a6900a4ee7fa0c19-0.parquet', ('mini_sweeper', 'plastic_dish_rack')),
}
BOX = {'A': [24, 13], 'B': [11, 31]}
eps = {}
for e, (run, base, pname, objs) in SRC.items():
    h = H.format(e)
    req = [f'refs/perc2{base}/ep{e}/processed/{h}/{pname}', f'refs/perc2{base}/ep{e}/reconstructed_stage/t3_ep{e:03d}_support.usda',
           f'refs/glockt/ep{e}/processed/{h}/ref_gl_ilc.parquet', f'refs/glockt/ep{e}/reconstructed_stage/t3_ep{e:03d}_support.usda']
    req += [f'refs/sf/ep{e}/assets/mesh/{o}/{o}.glb' for o in objs] + [f'refs/sf/ep{e}/assets/urdf/{o}_rigid.urdf' for o in objs]
    req += [f'results/glock_public/ep{e}/rest_check.json']
    opt = [f'results/glock_public/ep{e}/zero_score.txt', f'results/glock_public/ep{e}/support_fill.json']
    gp = f'{DL}/runs/{run}/refs/glockt/ep{e}/processed/{h}/ref_gl_ilc.parquet'
    gp = gp if os.path.exists(gp) else EP31
    t = pq.read_table(gp)
    urdf = {}
    for o in objs:
        u = f'{DL}/runs/{run}/refs/sf/ep{e}/assets/urdf/{o}_rigid.urdf'; txt = open(u).read()
        m, com, _ = mass_arm.read_inertial(txt)
        urdf[o] = dict(md5=mass_arm.md5(u), mass=m, com=com, meshes=sorted(set(re.findall(r'filename="([^"]+)"', txt))))
    eps[str(e)] = dict(source_run=run, base=base, mode='reuse', hive=h, pull=req, pull_optional=opt,
                       glockt_md5=mass_arm.md5(gp), glockt_fingerprint=mass_arm.traj_fingerprint(t),
                       object_body_names=t.column('object_body_names')[0].as_py(),
                       object_urdf_paths=t.column('object_urdf_paths')[0].as_py(), urdfs=urdf,
                       rest_check=json.load(open(f'{DL}/runs/{run}/results/glock_public/ep{e}/rest_check.json')),
                       box=[b for b, v in BOX.items() if e in v][0])
props = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../physics-2026-10-30/props_masses_only.json')
out = dict(note='Masses v2 (docs/research/work/masses-v2-20261031/PREREG.md): the 4 episodes and their stored finished grasp-lock '
                'references (reuse, never rebuilt). Paths are relative to runs/<source_run>/ in the HF store; ops/jobs/mass_check.sh '
                '(MV2_TAB) pulls each one with store.sh pull-files (one hf_hub_download, no listing) and places it at /content/<path>.',
           all_eps=[24, 11, 13, 31], boxes=BOX, props='docs/research/physics-2026-10-30/props_masses_only.json',
           props_md5=hashlib.md5(open(props, 'rb').read()).hexdigest(), episodes=eps)
json.dump(out, open(OUT, 'w'), indent=1)
print('wrote', OUT, {e: (v['source_run'], v['glockt_md5'][:8], v['glockt_fingerprint'][:8], len(v['pull'])) for e, v in eps.items()})
