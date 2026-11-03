"""Rack round R stage-1 table [D] from screen6.jsonl (copy of G3 stage1_table.py, rack only, 13i baseline, 6 picks): every
mesh sorted by CD-O median (6 seeds), with the stage-2 picks marked, plus per-model counts and medians.
Usage: stage1_table.py SCREEN.jsonl OUT.md"""
import json, sys

# the 13i rack's 50-seed C4 CD-O median (PREREG s14 step 4: G2 #17)
SH = dict(plastic_dish_rack=0.4016)
NPICK = 6
MODELS = ('sam3d', 'hy21', 'trellis2', 'trellis2_1024', 'pixal_mv', 'pixal_mv_1024')
recs = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
err = [r for r in recs if 'error' in r]
out = ['# Rack round R stage-1 screen [D]: 6 seeds 3001-3006, roster emptied, one scoring per generated mesh', '',
       'Public scans stand in for the hidden scans. Single-image models: the GT-free Sim(3) copy; Pixal3D-MV: the output in',
       'our object frame. CD-O in cm (median / mean of 6 seeds); W30 and FLIP = share of seeds with rotation error > 30 /',
       '> 90 deg; ADD and anchor = median over the seeds, mm (of the screened copy in our track frame, not of the placed',
       'copy). 13i = the 13i rack\'s 50-seed audit median (C4), so compare loosely (6 seeds, best-of-N here).',
       'Pick: T6 = one of the 6 lowest CD-O medians (stage 2, "cdo_top6").', '',
       f'{len(recs)} records, {len(err)} errors' + (f": {[r['label'] for r in err]}" if err else ''), '']
for o, ship in SH.items():
    rows = sorted([r for r in recs if r['object'] == o and 'screen' in r],
                  key=lambda r: (r['screen']['summary']['cdo_med'], r['screen']['summary']['cdo_mean'], r['label']))
    top = {r['label'] for r in rows[:NPICK]}
    nb = sum(r['screen']['summary']['cdo_med'] < ship for r in rows)
    out += [f'## {o} (13i 50-seed CD-O median {ship}; {len(rows)} meshes; {nb} with stage-1 CD-O median below it)', '']
    out += ['| model | n | best CD-O med | median of CD-O meds | W30 > 0 |', '|---|---|---|---|---|']
    for m in MODELS:
        c = [r['screen']['summary'] for r in rows if r['label'].split('/')[1] == m]
        if c:
            v = sorted(x['cdo_med'] for x in c)
            out.append(f'| {m} | {len(c)} | {v[0]:.4f} | {v[len(v) // 2]:.4f} | {sum(x["w30"] > 0 for x in c)} |')
    out += ['', '| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |',
            '|---|---|---|---|---|---|---|---|---|---|']
    for i, r in enumerate(rows, 1):
        s = r['screen']['summary']
        pick = 'T6' if r['label'] in top else ''
        if i > 20 and not pick:
            continue
        out.append(f"| {i} | {r['label']} | {s['cdo_med']:.4f} | {s['cdo_mean']:.4f} | {s['w30']} | {s['flip']} | "
                   f"{s['add_med']:.2f} | {s['anc_med']:.2f} | {s['amb_mm']:.2f} / {s['amb_floor_mm']:.2f} | {pick} |")
    out += ['', f'(rows 21-{len(rows)} omitted; all {len(rows)} are in screen/screen6.jsonl)', '']
open(sys.argv[2], 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
