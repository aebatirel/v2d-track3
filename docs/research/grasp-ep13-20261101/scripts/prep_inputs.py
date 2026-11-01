"""Local input trees for the CPU solver runs (2026-11-01, GRASP-mode test on public ep13; development on ep31).
Copies a stored reference (HF store mirror, run 20261030-orcB-38234d1) into OUT/<name>/processed/<seq>/<robot>/ref_in.parquet
with its reconstructed_stage/ support, and the episode's asset folder into OUT/<name>/assets. The ONLY change to the
parquet: object_urdf_paths point at the local asset copy instead of /content/refs/<sf|oracle_sf>/ep<N>/assets (the box
paths); every other column is checked byte-equal. No ground truth is read (the oracle reference is a stored diagnostic
input, used only on public ep13 as pre-registered).
Usage: python -I prep_inputs.py MIRROR OUT"""
import os, shutil, sys
import pyarrow as pa, pyarrow.parquet as pq

M, OUT = sys.argv[1], sys.argv[2]
R = f'{M}/runs/20261030-orcB-38234d1/refs'
JOBS = {  # name: (reference dir, asset dir, sequence, file)
    'ep13_P': ('glockt/ep13', 'sf/ep13', 't3_ep013', 'ref_gl_ilc.parquet'),
    'ep13_O': ('oracle_glockt/ep13', 'oracle_sf/ep13', 't3_ep013', 'ref_gl_ilc.parquet'),
    'ep31_P': ('glockt/ep31', 'sf/ep31', 't3_ep031', 'ref_gl_ilc.parquet'),
    # the support-filled references BEFORE the grasp lock (input of the two-hand grasp-lock rebuild, 1 Nov)
    'ep13_P_sf': ('sf/ep13', 'sf/ep13', 't3_ep013', 'ref_sf.parquet'),
    'ep13_O_sf': ('oracle_sf/ep13', 'oracle_sf/ep13', 't3_ep013', 'ref_sf.parquet'),
}
for name, (rd, ad, seq, fn) in JOBS.items():
    H = f'processed/sequence_id={seq}/robot_name=sharpa_wave'
    src = f'{R}/{rd}/{H}/{fn}'
    if not os.path.exists(src):
        print(name, 'missing', src); continue
    root = f'{OUT}/{name}'; os.makedirs(f'{root}/{H}', exist_ok=True); os.makedirs(f'{root}/reconstructed_stage', exist_ok=True)
    shutil.copytree(f'{R}/{ad}/assets', f'{root}/assets', dirs_exist_ok=True)
    for f in os.listdir(f'{R}/{rd}/reconstructed_stage'):
        shutil.copy(f'{R}/{rd}/reconstructed_stage/{f}', f'{root}/reconstructed_stage/{f}')
    t = pq.read_table(src); i = t.column_names.index('object_urdf_paths')
    old = t.column(i)[0].as_py(); pre = f'/content/refs/{ad}/assets/'
    assert all(u.startswith(pre) for u in old), old
    new = [f'{root}/assets/' + u[len(pre):] for u in old]
    t2 = t.set_column(i, 'object_urdf_paths', pa.array([new], type=t.schema.field(i).type))
    dst = f'{root}/{H}/ref_in.parquet'; pq.write_table(t2, dst); t3 = pq.read_table(dst)
    diff = [c for c in t.column_names if not t.column(c).equals(t3.column(c))]
    print(name, 'from', src.split('refs/')[1], '| columns differing:', diff, '| urdfs ->', [os.path.relpath(u, OUT) for u in new])
