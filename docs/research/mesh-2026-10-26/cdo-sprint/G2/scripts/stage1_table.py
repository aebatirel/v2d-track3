"""G2 stage-1 table [D] from screen6.jsonl: per object every mesh sorted by CD-O median (6 seeds), with the stage-2
picks marked, plus per-model counts and medians. Usage: stage1_table.py SCREEN.jsonl OUT.md"""
import collections, json, sys

SH = dict(white_pot=0.3107, blue_cup=0.2646, plastic_dish_rack=0.4182, water_pitcher=0.3713)
recs = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
out = ['# G2 stage-1 screen [D]: 6 seeds 3001-3006, roster emptied, one scoring per GT-free Sim(3) copy', '',
       'Public scans stand in for the hidden scans. CD-O in cm (median / mean of 6 seeds); W30 and FLIP = share of seeds',
       'with rotation error > 30 / > 90 deg; ADD and anchor = median over the seeds, mm (of the Sim(3) copy in our track',
       'frame, not of the placed copy). Shipped = the 13f mesh\'s 50-seed audit median (C4), so compare loosely.',
       'Pick: T4 = one of the 4 lowest CD-O medians (stage 2, "cdo_top4"); A = among the 2 lowest ADD medians with CD-O <=',
       'shipped + 0.005 ("add_ext" when not already T4).', '']
for o, ship in SH.items():
    rows = sorted([r for r in recs if r['object'] == o],
                  key=lambda r: (r['screen']['summary']['cdo_med'], r['screen']['summary']['cdo_mean'], r['label']))
    top = {r['label'] for r in rows[:4]}
    el = sorted([r for r in rows if r['screen']['summary']['cdo_med'] <= ship + 0.005],
                key=lambda r: (r['screen']['summary']['add_med'], r['screen']['summary']['cdo_med'], r['label']))
    low_add = {r['label'] for r in el[:2]}
    out += [f'## {o} (shipped 50-seed CD-O median {ship}; {len(rows)} meshes; {len(el)} with CD-O <= {ship + 0.005:.4f})', '']
    out += ['| model | n | best CD-O med | median of CD-O meds | W30 > 0 |', '|---|---|---|---|---|']
    for m in ('sam3d', 'hy21', 'trellis2', 'trellis2_1024'):
        c = [r['screen']['summary'] for r in rows if r['label'].split('/')[1] == m]
        if c:
            v = sorted(x['cdo_med'] for x in c)
            out.append(f'| {m} | {len(c)} | {v[0]:.4f} | {v[len(v) // 2]:.4f} | {sum(x["w30"] > 0 for x in c)} |')
    out += ['', '| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |',
            '|---|---|---|---|---|---|---|---|---|---|']
    for i, r in enumerate(rows, 1):
        s = r['screen']['summary']
        pick = ('T4' if r['label'] in top else '') + (' A' if r['label'] in low_add else '')
        if i > 12 and not pick:
            continue
        out.append(f"| {i} | {r['label']} | {s['cdo_med']:.4f} | {s['cdo_mean']:.4f} | {s['w30']} | {s['flip']} | "
                   f"{s['add_med']:.2f} | {s['anc_med']:.2f} | {s['amb_mm']:.2f} / {s['amb_floor_mm']:.2f} | {pick.strip()} |")
    out += ['', f'(rows 13-{len(rows)} omitted; all {len(rows)} are in screen/screen6.jsonl)', '']
open(sys.argv[2], 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
