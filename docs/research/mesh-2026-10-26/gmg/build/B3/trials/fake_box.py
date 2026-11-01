"""Dry run of tools/g0_report.py: a fake box output (the lid's and pot's own SHELL as the 'generated' mesh, identity
layout) in a dev run folder, so the report code path is exercised before the GPU results exist. Dev only; nothing
here is a result."""
import json, os, sys
MR = '/home/user/v2d-track3/docs/research/mesh-2026-10-26'
sys.path.insert(0, MR)
os.environ['GMG_MODE'] = 'dev'
from gmg import guard  # noqa
import numpy as np
run = sys.argv[1]; bundle = sys.argv[2]
guard.set_run(run)
from gmg.tools.g0_inputs import load_clean_bundle
from gmg.producers import shell as P_SHELL
from gmg.run_episode import _t0
b = load_clean_bundle(bundle)
t0, _ = _t0()
box = os.path.join(run, 'box', 'sam3d'); os.makedirs(box, exist_ok=True)
recs = []
for o, kind, k in (('white_pot_lid', 'primary', 132), ('white_pot', 'primary', 246)):
    c = P_SHELL.produce(dict(bundle=b, obj=o, t0=t0))[0]
    for seed in (0, 1):
        tag = f'ep2_{o}_{kind}_k{k}'
        p = os.path.join(box, f'{tag}_s{seed}.ply')
        c.mesh.export(p); guard.register_output(p)
        recs.append(dict(ok=True, tag=tag, seed=seed, obj=o, kind=kind, k=k, j=k + 1, path=os.path.basename(p),
                         obj_T_mesh=np.eye(4).tolist(), camA_T_mesh=np.eye(4).tolist(), sec=0.0))
lp = os.path.join(box, 'gen_log.jsonl')
with open(lp, 'w') as f:
    for r in recs:
        f.write(json.dumps(r) + '\n')
guard.register_output(lp)
guard.write_manifest(os.path.join(run, 'manifest_fake.json'), extra=dict(step='B3', what='fake box output (dry run)'))
print('fake box written', len(recs))
