"""CPU check (2026-10-31, arm S of the recipe screen, physics-solver.md section 9): the physS1 reference (arm C) vs the
physics-solved reference (arm S) per episode, from a local download of the store. Reads only reference
parquets (no ground truth). Reports md5s, whether the solved file is the copy G3 trained on (psolverl refs/glockt), whether
its solver input is the physS1 file, every differing column (max abs diff), object-column identity, support stages and
URDF roots. Usage: solved_refs_check.py DL_ROOT (holding runs/20261030-physS1-6a814df/refs/glockt and
runs/20261030-psolverl-04301a2/refs/{psolve,psolve2,glockt})"""
import hashlib, json, os, sys
import numpy as np, pyarrow.parquet as pq
D = sys.argv[1]
B = f'{D}/runs/20261030-physS1-6a814df/refs/glockt'
PSR = f'{D}/runs/20261030-psolverl-04301a2/refs'
SUB = {2: 'psolve2', 12: 'psolve2', 18: 'psolve', 24: 'psolve'}
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()
hv = lambda e: f'processed/sequence_id=t3_ep{e:03d}/robot_name=sharpa_wave'
out = {}
for e in (2, 12, 18, 24):
    pb = f'{B}/ep{e}/{hv(e)}/ref_gl_ilc.parquet'; ps = f'{PSR}/{SUB[e]}/ep{e}/{hv(e)}/ref_ps.parquet'
    pin = f'{PSR}/{SUB[e]}/ep{e}/{hv(e)}/ref_in.parquet'; pg3 = f'{PSR}/glockt/ep{e}/{hv(e)}/ref_gl_ilc.parquet'
    tb, ts = pq.read_table(pb), pq.read_table(ps)
    r = dict(physS1_md5=md5(pb), solved_md5=md5(ps), solved_src=f'{SUB[e]}/ep{e}', solver_input_md5=md5(pin),
             solver_input_is_physS1=md5(pin) == md5(pb), solved_equals_input=md5(ps) == md5(pin),
             g3_training_copy_md5=md5(pg3), solved_is_g3_training_file=md5(pg3) == md5(ps),
             rows=(tb.num_rows, ts.num_rows), same_schema=tb.schema.equals(ts.schema), same_columns=tb.column_names == ts.column_names)
    diff = {}
    for c in tb.column_names:
        a, b = tb.column(c).to_pylist(), ts.column(c).to_pylist()
        if a == b:
            continue
        try:
            x, y = np.asarray(a[0], float), np.asarray(b[0], float)
            d = np.abs(x - y); diff[c] = dict(shape=list(x.shape), max_abs=float(d.max()), n_diff=int((d > 0).sum()), n=int(d.size))
        except Exception as ex:
            diff[c] = dict(error=str(ex)[:100])
    r['differing_columns'] = diff
    obj = [c for c in tb.column_names if c.startswith('object')]
    r['object_columns'] = obj
    r['object_columns_identical'] = all(tb.column(c).to_pylist() == ts.column(c).to_pylist() for c in obj)
    r['non_robot_columns_differing'] = [c for c in diff if not c.startswith('robot_')]
    st = {}
    for name, root in (('physS1', f'{B}/ep{e}'), ('solved', f'{PSR}/{SUB[e]}/ep{e}'), ('g3', f'{PSR}/glockt/ep{e}')):
        f = f'{root}/reconstructed_stage/t3_ep{e:03d}_support.usda'; st[name] = md5(f) if os.path.exists(f) else None
    r['support_stage_md5'] = st; r['support_stage_identical'] = len(set(st.values())) == 1
    r['urdf_roots'] = sorted({os.path.dirname(os.path.dirname(p)) for p in ts.column('object_urdf_paths')[0].as_py()})
    r['urdf_roots_physS1'] = sorted({os.path.dirname(os.path.dirname(p)) for p in tb.column('object_urdf_paths')[0].as_py()})
    out[f'ep{e}'] = r
print(json.dumps(out, indent=1))
