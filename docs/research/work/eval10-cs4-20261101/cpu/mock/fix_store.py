"""Test-only edits of the cavity-safe retrain mock (setup.sh): rewrite the stored V's asset paths to this mock's content root
(on a real box both are /content), update e10v's arms.json md5 in the fake store, and set the repo COPY's tools/e10cs.py V pins
to the mock V. Usage: fix_store.py MR E10V_MR. Writes MR/test_edits.json."""
import glob, hashlib, json, os, re, sys
import pyarrow as pa, pyarrow.parquet as pq

MR, EM = sys.argv[1].rstrip('/'), sys.argv[2].rstrip('/')
sys.path.insert(0, f'{MR}/content/v2d-track3/tools')
from mass_arm import traj_fingerprint   # noqa: E402
ST = f'{MR}/store/runs/20261031-e10v-caf38fb'; md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest()
V = glob.glob(f'{ST}/refs/perc2e10v_glockt/ep10/processed/*/*/ref_gl_ilc.parquet'); assert len(V) == 1, V
V = V[0]; t = pq.read_table(V); before = md5(V); fp0 = traj_fingerprint(t)
cols = {}
for c in ('object_urdf_paths', 'object_mesh_paths'):
    cols[c] = [[p.replace(f'{EM}/content/', f'{MR}/content/') for p in t.column(c)[0].as_py()]]
for c, v in cols.items():
    t = t.set_column(t.column_names.index(c), c, pa.array(v, type=t.schema.field(c).type))
pq.write_table(t, V); after = md5(V); fp1 = traj_fingerprint(pq.read_table(V))
assert fp0 == fp1, 'fingerprint changed'
A = f'{ST}/results/ev10_v4p/arms.json'; arms = json.load(open(A)); arms['source_md5'] = after; json.dump(arms, open(A, 'w'), indent=1)
base = glob.glob(f'{ST}/refs/perc2e10vmck/ep10/processed/*/*/*.parquet'); assert len(base) == 1, base
bmd5 = md5(base[0]); assert bmd5 == arms['base_md5'], (bmd5, arms['base_md5'])
E = f'{MR}/content/v2d-track3/tools/e10cs.py'; s = open(E).read()
s2 = re.sub(r"V_MD5, V_FP, BASE_MD5 = '[0-9a-f]{32}', '[0-9a-f]{32}', '[0-9a-f]{32}'",
            f"V_MD5, V_FP, BASE_MD5 = '{after}', '{fp1}', '{bmd5}'", s)
assert s2 != s, 'pins not found'; open(E, 'w').write(s2)
rec = dict(v_parquet=V.replace(MR, '<MR>'), v_md5_before=before, v_md5_after=after, fingerprint=fp1, base_md5=bmd5,
           urdf_paths_after=[p.replace(MR, '<MR>') for p in cols['object_urdf_paths'][0]],
           e10cs_py_pins='V_MD5 / V_FP / BASE_MD5 of the repo copy set to the mock V (real values: 5d22fc57... / 8f408d51... / ca4ae8dc...)')
json.dump(rec, open(f'{MR}/test_edits.json', 'w'), indent=1)
print('fix_store:', json.dumps(rec))
