"""Overnight A/B table (2026-10-22): collect hard_ab.sh repeat-evaluation summaries from box copies and print a markdown
table per episode (registered AUC with our meshes and sim_vs_ref, mean ± std and range over the repeat evaluations;
difference of the mean to the base policy). Usage: ab_table.py DIR [DIR ...] where each DIR holds
results/hard_ab/ep<N>/<variant>/summary.json (e.g. the scratchpad copies boxres/<run_id>/).
Variant names: base = mc / mcs (published policy); <base>k = contact retargeting, <base>kq = k + object keypoints at
0.15 m, <base>p = primitive-collision hand, <base>kp = k + primitive, i = + deployment-exact starts; suffix -s<seed>."""
import glob, json, os, re, sys

LABEL = {'k': 'contact retargeting', 'kq': 'retargeting + keypoints 0.15 m', 'p': 'primitive hand',
         'kp': 'retargeting + primitive hand', 'ki': 'retargeting + deployment-exact starts',
         'kpi': 'retargeting + primitive hand + deployment-exact starts',
         'kri': 'retargeting + rest settle + deployment-exact starts', 'i': 'deployment-exact starts', 'kfi': 'kri + flattened sweeper base (library_v3)', 'kr': 'retargeting + rest settle', 'ks': 'retargeting, PUBLIC scan assets (oracle mesh)', 'pi': 'primitive hand + deployment-exact starts',
         'kd': 'retargeting + FDR rewards (object points, fingertip bound)', 'kfid': 'kfi + FDR rewards (object points, fingertip bound)',
         '': 'base (published policy)'}
rows = {}
for d in sys.argv[1:]:
    for f in glob.glob(os.path.join(d, 'results/hard_ab/ep*/*/summary.json')):
        ep = int(f.split('/')[-3][2:]); var = f.split('/')[-2]
        try:
            s = json.load(open(f))
        except Exception:
            continue
        rows.setdefault(ep, {})[var] = dict(s, box=os.path.basename(os.path.normpath(d)))


def kind(var):
    m = re.match(r'^(mcs|mc|m)(kfid|kfi|kri|kpi|kp|kq|kr|ks|kd|ki|k|pi|p|i)?(?:-s(\d+))?$', var)
    return (m.group(1), m.group(2) or '', int(m.group(3)) if m.group(3) else 42) if m else (var, '?', 0)


def fmt(a):
    return f"{a['mean']:.3f} ± {a['std']:.3f} ({a['min']:.3f}–{a['max']:.3f})" if a else '–'


for ep in sorted(rows):
    vs = rows[ep]; base = next((v for v in vs if kind(v)[1] == ''), None)
    b = vs[base]['auc']['mean'] if base and vs[base].get('auc') else None
    print(f'\n**ep{ep}**\n\n| variant | change | seed | n | registered AUC | sim_vs_ref | Δ AUC mean vs base |\n|---|---|---|---|---|---|---|')
    for v in sorted(vs, key=lambda v: (kind(v)[1] != '', kind(v)[1], kind(v)[2])):
        s = vs[v]; a = s.get('auc'); _, k, seed = kind(v)
        d = f"{a['mean'] - b:+.3f}" if (a and b is not None and k) else ''
        print(f"| {v} | {LABEL.get(k, k)} | {seed} | {s.get('n', 0)} | {fmt(a)} | {fmt(s.get('sim_vs_ref'))} | {d} |")
