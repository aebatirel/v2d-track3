"""G3 stage-1 screen manifest (copy of G2's, G3 objects, plus Pixal3D-MV): every screened mesh listed in the frozen
SHA256SUMS -> label g3/<model>/<tag>, object, absolute path under ROOT. The file on disk must match its frozen hash, else
it is left out and reported.
  single-image models: the GT-free Sim(3) copy gen/<model>_sim3/<tag>.ply (tag ep<E>_<object>_k<k>_s<seed>);
  Pixal3D-MV: the output in our object frame gen/pixal_mv[_1024]/<tag>.ply (tag ep<E>_<object>_s<seed>; not *_gen.ply).
Usage: screen_manifest.py SHA256SUMS ROOT OUT.tsv      (ROOT = the folder that holds gen/)
"""
import hashlib, os, sys

sums, root, out = sys.argv[1:4]
OBJ = ('mini_dust_pan', 'beige_cup', 'white_pot_lid', 'mini_sweeper', 'wooden_piece_1', 'wooden_piece_2',
       'plastic_dish_rack', 'white_pot')
rows, bad = [], []
for l in open(sums):
    h, rel = l.split()
    parts = rel.split('/')
    if len(parts) != 3:
        continue
    if parts[1].endswith('_sim3'):
        model = parts[1][:-len('_sim3')]
    elif parts[1] in ('pixal_mv', 'pixal_mv_1024') and not parts[2].endswith('_gen.ply'):
        model = parts[1]
    else:
        continue
    tag = parts[2][:-len('.ply')]
    rest = tag.split('_', 1)[1]
    obj = next(o for o in OBJ if rest.startswith(o + '_k') or rest.startswith(o + '_s'))
    p = os.path.join(root, rel)
    if hashlib.sha256(open(p, 'rb').read()).hexdigest() != h:
        bad.append(rel); continue
    rows.append(f'g3/{model}/{tag}\t{obj}\t{p}')
open(out, 'w').write('\n'.join(rows) + '\n')
print(f'{len(rows)} meshes -> {out}; hash mismatches: {bad}')
