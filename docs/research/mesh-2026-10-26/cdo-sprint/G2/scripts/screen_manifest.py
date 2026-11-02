"""G2 stage-1 screen manifest: every GT-free Sim(3) copy listed in the frozen SHA256SUMS (gen/<model>_sim3/<tag>.ply,
tag ep<E>_<object>_k<k>_s<seed>) -> label g2/<model>/<tag>, object, absolute path under ROOT. The file on disk must match
its frozen hash, else it is left out and reported.
Usage: screen_manifest.py SHA256SUMS ROOT OUT.tsv      (ROOT = the folder that holds gen/)
"""
import hashlib, os, sys

sums, root, out = sys.argv[1:4]
OBJ = ('white_pot', 'blue_cup', 'plastic_dish_rack', 'water_pitcher')
rows, bad = [], []
for l in open(sums):
    h, rel = l.split()
    parts = rel.split('/')
    if len(parts) != 3 or not parts[1].endswith('_sim3'):
        continue
    model, tag = parts[1][:-len('_sim3')], parts[2][:-len('.ply')]
    obj = next(o for o in OBJ if tag.split('_', 1)[1].startswith(o + '_k'))
    p = os.path.join(root, rel)
    if hashlib.sha256(open(p, 'rb').read()).hexdigest() != h:
        bad.append(rel); continue
    rows.append(f'g2/{model}/{tag}\t{obj}\t{p}')
open(out, 'w').write('\n'.join(rows) + '\n')
print(f'{len(rows)} meshes -> {out}; hash mismatches: {bad}')
