"""Freeze the batch-2 generated meshes and write the one-shot scoring manifest (2026-10-29).

Pre-registered (work log, before any scan was read for these meshes):
  - every generated mesh file (raw generator output, object-frame Pixal3D output, Sim(3)-fitted copies) gets a sha256
    line in SHA256SUMS; nothing is regenerated or edited after this;
  - scored once each, with mesh_metric.py: Pixal3D-MV (all view sets and seeds, plus the view-0-only runs) in our
    object frame as generated; for the single-image models (TRELLIS.2, TripoSG, Hunyuan3D-2.1, SAM 3D) the Sim(3)
    copy fitted to our observed points (CD-O is similarity-invariant, so it equals the raw mesh's CD-O; ADD and flips
    are only meaningful in our frame), first-ranked crop of crops.py (chosen[0]) x seeds 42 and 7. The second crop
    (an adjacent frame of the same view) is generated but not scored, to keep the scan reads and CPU bounded.
Usage: gen_manifest.py RUNDIR CROPSDIR OUT.tsv
"""
import hashlib, json, os, sys

run, crops, out = sys.argv[1:4]
G = os.path.join(run, 'results', 'gen')
EPS = dict(white_pot=41, white_pot_lid=2, blue_cup=22, water_pitcher=22, wooden_piece_1=23, wooden_piece_2=23,
           plastic_dish_rack=26, mini_sweeper=31, mini_dust_pan=39, beige_cup=11)
lines = []
for root, _, files in sorted(os.walk(G)):
    for f in sorted(files):
        if f.endswith('.ply'):
            p = os.path.join(root, f)
            lines.append(f'{hashlib.sha256(open(p, "rb").read()).hexdigest()}  {os.path.relpath(p, run)}')
open(os.path.join(run, 'SHA256SUMS'), 'w').write('\n'.join(lines) + '\n')
first = {o: json.load(open(f'{crops}/ep{e}/{o}_crops.json'))['chosen'][0]['k'] for o, e in EPS.items()}
rows = []
for o, e in EPS.items():
    for sub, suf in (('pixal_mv', ''), ('pixal_v1', '_v1')):
        for s in (42, 7):
            p = os.path.join(G, sub, f'ep{e}_{o}{suf}_s{s}.ply')
            if os.path.exists(p):
                rows.append((f'gen/{sub}/ep{e}_{o}_s{s}', o, p, sub))
    for m in ('trellis2', 'triposg', 'hy21', 'sam3d'):
        for s in (42, 7):
            p = os.path.join(G, f'{m}_sim3', f'{o}_k{first[o]}_s{s}.ply')
            if os.path.exists(p):
                rows.append((f'gen/{m}/ep{e}_{o}_k{first[o]}_s{s}', o, p, m))
            else:
                print('missing', m, o, s, file=sys.stderr)
open(out, 'w').write(''.join('\t'.join(map(str, r)) + '\n' for r in rows))
print(f'{len(lines)} meshes hashed; {len(rows)} to score -> {out}')
