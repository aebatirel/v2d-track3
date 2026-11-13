"""Populate the Masses v2 mock store (setup_v2.sh). usage: store_v2.py STORE MR. For every episode of the REAL table
(refs_v2.json) and every file of its pull lists, STORE/runs/<source_run>/<path> is the real store file when it was
downloaded (scratchpad massv2/dl, single-file downloads; ep31's glockt parquet from an earlier local copy), else a labelled
stand-in. Parquet asset paths /content/ -> MR/content/. Writes STORE/mock_table_diff.json and STORE/.populated."""
import glob, hashlib, json, os, shutil, sys
import pyarrow as pa, pyarrow.parquet as pq
STORE, MR = sys.argv[1], sys.argv[2]
R = '/home/user/v2d-track3'; S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
DL = f'{S}/massv2/dl'; EP31 = f'{S}/oracle/dl_ref'
sys.path.insert(0, f'{R}/tools')
from mass_arm import traj_fingerprint, md5   # noqa: E402
T = json.load(open(f'{R}/docs/research/work/masses-v2-20261031/refs_v2.json'))
diff, prov = dict(episodes={}), {}


def repoint(src, dst, to_assets=False):
    t = pq.read_table(src)
    names = t.column('object_body_names')[0].as_py()
    for c in ('object_urdf_paths', 'object_mesh_paths'):
        if c in t.column_names:
            v = [p.replace('/content/', MR + '/content/', 1) for p in t.column(c)[0].as_py()]
            if to_assets:     # a base reference names /content/assets (make_assets output), as the real ones do
                v = [f'{MR}/content/assets/urdf/{n}_rigid.urdf' if c == 'object_urdf_paths' else f'{MR}/content/assets/mesh/{n}/{n}.glb' for n in names]
            t = t.set_column(t.column_names.index(c), c, pa.array([v], type=t.schema.field(c).type))
    os.makedirs(os.path.dirname(dst), exist_ok=True); pq.write_table(t, dst)


for e, v in T['episodes'].items():
    run = v['source_run']; base = f'{STORE}/runs/{run}'
    for p in v['pull'] + v['pull_optional']:
        dst = f'{base}/{p}'; os.makedirs(os.path.dirname(dst), exist_ok=True)
        real = [x for x in (f'{DL}/runs/{run}/{p}', f'{EP31}/runs/{run}/{p}') if os.path.exists(x)]
        if p.endswith('ref_gl_ilc.parquet'):
            repoint(real[0], dst); prov[f'{run}/{p}'] = 'REAL (asset paths re-pointed)'
        elif '/processed/' in p and p.endswith('.parquet'):
            g = [x for x in (f'{DL}/runs/{run}/refs/glockt/ep{e}/processed/{v["hive"]}/ref_gl_ilc.parquet',
                             f'{EP31}/runs/{run}/refs/glockt/ep{e}/processed/{v["hive"]}/ref_gl_ilc.parquet') if os.path.exists(x)][0]
            repoint(g, dst, to_assets=True); prov[f'{run}/{p}'] = 'STAND-IN (the glockt parquet, asset paths -> /content/assets)'
        elif real:
            shutil.copy(real[0], dst); prov[f'{run}/{p}'] = 'REAL'
        elif p.endswith('.glb'):
            shutil.copy(f'{R}/meshes/library_v3/{os.path.basename(p)}', dst); prov[f'{run}/{p}'] = 'STAND-IN (library_v3 glb)'
        elif p.endswith('.usda'):
            open(dst, 'w').write('#usda 1.0\n# mock support stage (stand-in)\n'); prov[f'{run}/{p}'] = 'STAND-IN'
        elif p.endswith('zero_score.txt'):
            open(dst, 'w').write('zero_action: 0.5000 (mock stand-in)\n'); prov[f'{run}/{p}'] = 'STAND-IN'
        else:
            json.dump(dict(mock='stand-in'), open(dst, 'w')); prov[f'{run}/{p}'] = 'STAND-IN'
    g = f'{base}/refs/glockt/ep{e}/processed/{v["hive"]}/ref_gl_ilc.parquet'
    fp = traj_fingerprint(pq.read_table(g))
    assert fp == v['glockt_fingerprint'], (e, fp)
    diff['episodes'][e] = dict(fingerprint=fp, real_md5=v['glockt_md5'], mock_md5=md5(g))
json.dump(dict(diff, provenance=prov), open(f'{STORE}/mock_table_diff.json', 'w'), indent=1)
open(f'{STORE}/.populated', 'w').write('ok\n')
print('store populated:', {k: sum(1 for x in prov.values() if x.startswith(k)) for k in ('REAL', 'STAND-IN')})
