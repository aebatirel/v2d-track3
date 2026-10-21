"""How much do mesh defects cost under the kit's registered Track 3 scoring? (diagnostic, public episodes only)

Writes damaged copies of the public scans (the registration stand-in stays the clean scan) and scores the same
perception trajectory with each, through score_registered.py. Damage modes (in the scan's body frame):
  clean      the scan itself (decimated by the packer's budget_mesh, as in a submission)
  scale110   uniformly scaled by 1.10 about the origin (registration normalises scale; poses are not rescaled)
  noise3mm   Gaussian vertex noise, sigma 3 mm
  inflate5mm every vertex moved 5 mm along its normal
  hull       convex hull (concavities lost: pot inside, rack slots, cup inside)
  cut20      faces whose centroid lies in the lowest 20 % of the body z extent removed (an unseen bottom; open mesh)
  cut20side  faces in the 20 % slab along body +x removed (an unseen side)
Usage: python mesh_sensitivity.py EP POSES_WORLD_VO_NPZ OUTDIR [--t3 ..] [--kit ..] [--modes clean,hull,...]
"""
import argparse, json, os, subprocess, sys
import numpy as np, trimesh

p = argparse.ArgumentParser()
p.add_argument('ep', type=int); p.add_argument('poses'); p.add_argument('outdir')
p.add_argument('--t3', default='/content/t3'); p.add_argument('--kit', default='/content/kit/v2d_submission_kit')
p.add_argument('--modes', default='clean,scale110,noise3mm,inflate5mm,hull,cut20,cut20side')
a = p.parse_args()
import pyarrow.parquet as pq
names = [str(o['name']) for o in pq.read_table(f'{a.t3}/ep{a.ep}.parquet').to_pandas()['observation.objects'].iloc[0]]


def scan(n):
    q = f'{a.t3}/mesh/{n}/{n}.glb'
    return trimesh.load(q if os.path.exists(q) else f'{a.t3}/mesh/{n}/{n}_visual.glb', force='mesh')


def damage(m, mode, rng):
    m = m.copy()
    if mode == 'scale110':
        m.apply_scale(1.10)
    elif mode == 'noise3mm':
        m.vertices = m.vertices + rng.normal(0, 0.003, m.vertices.shape)
    elif mode == 'inflate5mm':
        m.vertices = m.vertices + 0.005 * m.vertex_normals
    elif mode == 'hull':
        m = m.convex_hull
    elif mode in ('cut20', 'cut20side'):
        ax = 2 if mode == 'cut20' else 0
        c = m.triangles_center[:, ax]; lo, hi = m.bounds[0, ax], m.bounds[1, ax]
        keep = c > lo + 0.2 * (hi - lo) if mode == 'cut20' else c < hi - 0.2 * (hi - lo)
        m.update_faces(keep); m.remove_unreferenced_vertices()
    return m


S = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'score_registered.py')
summary = {}
for mode in a.modes.split(','):
    d = os.path.join(a.outdir, mode); os.makedirs(d, exist_ok=True)
    rng = np.random.default_rng(0)
    for n in names:
        damage(scan(n), mode, rng).export(f'{d}/{n}.glb')
    out = f'{d}/score.json'
    subprocess.run([sys.executable, '-I', S, str(a.ep), a.poses, '--meshes', d, '--t3', a.t3, '--kit', a.kit,
                    '--out', out], check=True, stdout=subprocess.DEVNULL)
    r = json.load(open(out))
    summary[mode] = dict(AUC=r['perception']['AUC'], SP=r['perception']['SP_SR'], MP=r['perception']['MP_SR'],
                         MPPE=r['perception']['MPPE_cm'], reg={k: (v['rot_deg'], v['anchor_shift_cm'])
                                                              for k, v in r['registration'].items()})
    print(a.ep, mode, summary[mode], flush=True)
json.dump(summary, open(os.path.join(a.outdir, f'sensitivity_ep{a.ep}.json'), 'w'), indent=1)
