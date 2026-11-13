"""One-off reference values for the gmg's copy of the self-ambiguity (B5): runs the ORIGINAL
scripts/mesh_metric.ambiguity (which calls the kit's AUC.py helpers) on the synthetic meshes of
gmg/tests/amb_meshes.py and writes gmg/tests/fixtures/amb_reference.json. Run OUTSIDE the gmg (no gmg import): the
gmg never imports mesh_metric (SPEC section 2). GT-free: ambiguity() reads no file; mesh_metric's import reads the
kit roster and config and loads the kit metric code (no scan; checked by strace, B5 notes). Zero scan scorings.

  python gmg/build/b5/amb_reference.py      (cwd docs/research/mesh-2026-10-26, venv python)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GMG = os.path.dirname(os.path.dirname(HERE))
MR = os.path.dirname(GMG)
sys.path.insert(0, os.path.join(MR, 'scripts'))
sys.path.insert(0, os.path.join(GMG, 'tests'))
import numpy as np  # noqa: E402
import mesh_metric  # noqa: E402
import amb_meshes as AM  # noqa: E402

out = {}
for name, (fn, kind) in AM.RECIPES.items():
    m = fn()
    v, f = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
    r = mesh_metric.ambiguity(v, f, kind)
    out[name] = dict(kind=kind, faces=int(len(f)), vertices=int(len(v)),
                     **{k: (None if isinstance(x, float) and not np.isfinite(x) else x) for k, x in r.items()})
    print(name, out[name], flush=True)
dst = os.path.join(GMG, 'tests', 'fixtures', 'amb_reference.json')
with open(dst, 'w') as fh:
    json.dump(dict(source='scripts/mesh_metric.ambiguity (original, kit AUC.py helpers)', script=os.path.relpath(
        __file__, MR), meshes='gmg/tests/amb_meshes.py RECIPES', values=out), fh, indent=1)
print('wrote', dst)
