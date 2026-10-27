"""Collect the refcheck/chain scores into tables (refcheck/chain, 26 Oct 2026; reads only the score JSONs).
Usage: python -I compile.py SCORES_DIR OUT_DIR   -> OUT_DIR/results.json, OUT_DIR/tables.md
"""
import json, os, sys
import numpy as np

SD, OUT = sys.argv[1], sys.argv[2]
PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
CAN = [2, 11, 12, 18, 21, 24, 26, 27, 31, 39]
GUARD = [0, 11, 12, 18, 21, 23, 24, 31]
STALE = [0, 13, 22, 23, 40, 41, 42, 43, 44, 45]
SHORT = dict(white_pot='pot', white_pot_lid='lid', blue_cup='blue', beige_cup='beige', plastic_dish_rack='rack',
             mini_sweeper='sweeper', mini_dust_pan='pan', water_pitcher='pitcher', wooden_piece_1='board',
             wooden_piece_2='board')
MIDPOINT = dict(pot=0.97, lid=0.965, blue=0.95, beige=0.93, rack=0.95, sweeper=0.96, pan=0.95, pitcher=0.66, board=0.82)


def load(tag, key='perception'):
    f = f'{SD}/{tag}.json'
    if not os.path.exists(f):
        return None
    d = json.load(open(f))
    return dict(AUC=d[key]['AUC'], obj=d[key]['per_obj_AUC'], reg=d['registration'], objects=d['objects'])


R = dict(chain={}, sweep={}, guard={}, stale={})
for ep in CAN:
    row = {}
    for lib in ('lib', 'scan'):
        row[f'perc_{lib}'] = load(f'can_ep{ep}_perc_{lib}')
        row[f'e2s_{lib}'] = load(f'can_ep{ep}_e2s_{lib}')
        row[f'ref_{lib}'] = load(f'can_ep{ep}_res_{lib}', 'reference')
        row[f'sim_{lib}'] = load(f'can_ep{ep}_res_{lib}', 'sim')
        row[f'floor_{lib}'] = load(f'can_ep{ep}_res_{lib}', 'static_floor')
    row['proc_lib'] = load(f'can_ep{ep}_proc_lib')
    R['chain'][ep] = row
for ep in PUBLIC:
    R['sweep'][ep] = {lib: load(f'sweep_ep{ep}_{lib}') for lib in ('lib', 'scan')}
for ep in GUARD:
    R['guard'][ep] = {lib: load(f'guard_ep{ep}_{lib}') for lib in ('lib', 'scan')}
for ep in STALE:
    R['stale'][ep] = {k: load(f'stale_ep{ep}_{k}_scan') for k in ('perc', 'ref')}


def f4(x):
    return '' if x is None else f'{x:.3f}'


def g(r, k, n=None):
    v = r.get(k)
    if v is None:
        return None
    return v['AUC'] if n is None else v['obj'][n]


L = []
# ---- 1. chain table
L.append('### Chain per episode and object (registered ADD AUC vs public mocap)\n')
L.append('lib = our submitted meshes (library_v3; ep11 library_v3x), scan = public scans. perc = perception that fed the '
         'reference; e2s = mkref output before contact retarget; ref = final reference (evaluator reference columns); '
         'sim = rollout r1. d_mkref = e2s - perc, d_cr = ref - e2s, reg = lib - scan.\n')
L.append('| ep | object | perc lib | e2s lib | ref lib | d_mkref | d_cr | ref-perc | perc scan | e2s scan | ref scan | reg (perc) | reg (ref) | sim lib | sim scan |')
L.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
flags = []
for ep in CAN:
    r = R['chain'][ep]
    if r['perc_lib'] is None:
        continue
    names = r['perc_lib']['objects']
    for n in names + ['(scene)']:
        k = None if n == '(scene)' else n
        pl, el, rl = g(r, 'perc_lib', k), g(r, 'e2s_lib', k), g(r, 'ref_lib', k)
        ps, es, rs = g(r, 'perc_scan', k), g(r, 'e2s_scan', k), g(r, 'ref_scan', k)
        sl, ss = g(r, 'sim_lib', k), g(r, 'sim_scan', k)
        dm = None if el is None or pl is None else el - pl
        dc = None if el is None or rl is None else rl - el
        L.append(f'| {ep} | {n} | {f4(pl)} | {f4(el)} | {f4(rl)} | {f4(dm)} | {f4(dc)} | {f4(None if rl is None else rl - pl)} | '
                 f'{f4(ps)} | {f4(es)} | {f4(rs)} | {f4(pl - ps)} | {f4(None if rl is None else rl - rs)} | {f4(sl)} | {f4(ss)} |')
        if rl is not None and rl < pl - 0.01:
            flags.append(dict(kind='ref_below_perc', ep=ep, object=n, perc_lib=pl, ref_lib=rl, e2s_lib=el))
        if rs is not None and rs < ps - 0.01:
            flags.append(dict(kind='ref_below_perc_scan', ep=ep, object=n, perc_scan=ps, ref_scan=rs, e2s_scan=es))
        if pl < ps - 0.03:
            flags.append(dict(kind='lib_below_scan_perc', ep=ep, object=n, lib=pl, scan=ps))
        if rl is not None and rl < rs - 0.03:
            flags.append(dict(kind='lib_below_scan_ref', ep=ep, object=n, lib=rl, scan=rs))
    pr = r['proc_lib']
    if pr is not None and r['ref_lib'] is not None and abs(pr['AUC'] - r['ref_lib']['AUC']) > 1e-4:
        flags.append(dict(kind='CONVERSION_MISMATCH', ep=ep, proc=pr['AUC'], ref=r['ref_lib']['AUC']))
R['flags_chain'] = flags

# ---- 2. sweep / guard table
L.append('\n### Perception sweep (base arm, 20 episodes) and track-guard arm (8), re-scored\n')
L.append('| ep | object | sweep lib | sweep scan | reg | guard lib | guard scan | box-stored sweep (library_v2) |')
L.append('|---|---|---|---|---|---|---|---|')
box = {}
for ep in PUBLIC:
    f = f'/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck/store/runs/20261025-sweep-a894083/results/sweep/base/ep{ep}/score_registered.json'
    if os.path.exists(f):
        d = json.load(open(f)); box[ep] = d['perception']
sflags = []
for ep in PUBLIC:
    s = R['sweep'][ep]
    if s['lib'] is None:
        continue
    gd = R['guard'].get(ep, {})
    for n in s['lib']['objects'] + ['(scene)']:
        k = None if n == '(scene)' else n
        sl, ss = g(s, 'lib', k), g(s, 'scan', k)
        gl, gs = (g(gd, 'lib', k), g(gd, 'scan', k)) if gd else (None, None)
        bx = None if ep not in box else (box[ep]['AUC'] if k is None else box[ep]['per_obj_AUC'][k])
        L.append(f'| {ep} | {n} | {f4(sl)} | {f4(ss)} | {f4(None if ss is None else sl - ss)} | {f4(gl)} | {f4(gs)} | {f4(bx)} |')
        if ss is not None and sl < ss - 0.03:
            sflags.append(dict(kind='lib_below_scan_sweep', ep=ep, object=n, lib=sl, scan=ss))
        if gs is not None and gl < gs - 0.03:
            sflags.append(dict(kind='lib_below_scan_guard', ep=ep, object=n, lib=gl, scan=gs))
R['flags_sweep'] = sflags

# ---- 3. per-object means
def per_object(rows):
    acc = {}
    for ep, n, v in rows:
        if v is not None:
            acc.setdefault(SHORT[n], []).append((ep, v))
    return {o: dict(mean=round(float(np.mean([v for _, v in xs])), 4), min=round(float(np.min([v for _, v in xs])), 4),
                    n=len(xs), eps=[e for e, _ in xs]) for o, xs in acc.items()}


def rows_of(table, key, eps):
    out = []
    for ep in eps:
        t = table.get(ep, {})
        v = t.get(key)
        if v is None:
            continue
        for n in v['objects']:
            out.append((ep, n, v['obj'][n]))
    return out


cur = {}            # newest perception: guard arm where it exists, else sweep base
for ep in PUBLIC:
    cur[ep] = R['guard'][ep] if ep in R['guard'] and R['guard'][ep]['lib'] is not None else R['sweep'][ep]
T = dict(sweep_lib=per_object(rows_of(R['sweep'], 'lib', PUBLIC)), sweep_scan=per_object(rows_of(R['sweep'], 'scan', PUBLIC)),
         newest_lib=per_object(rows_of(cur, 'lib', PUBLIC)), newest_scan=per_object(rows_of(cur, 'scan', PUBLIC)),
         ref_lib=per_object(rows_of(R['chain'], 'ref_lib', CAN)), ref_scan=per_object(rows_of(R['chain'], 'ref_scan', CAN)),
         perc_can_lib=per_object(rows_of(R['chain'], 'perc_lib', CAN)), e2s_can_lib=per_object(rows_of(R['chain'], 'e2s_lib', CAN)))
T['newest_lib_excl_identity_fail'] = per_object([r for r in rows_of(cur, 'lib', PUBLIC) if r[0] != 23])
T['newest_scan_excl_identity_fail'] = per_object([r for r in rows_of(cur, 'scan', PUBLIC) if r[0] != 23])
R['per_object'] = T
L.append('\n### Per-object mean AUC over public episodes (n = object-episodes)\n')
L.append('newest perc = guard arm where it exists (0, 11, 12, 18, 21, 23, 24, 31), else sweep base; excl. ep23 = without the '
         'frame-0 board swap of ep23 (identity failure, the boards then score 0.08 / 0.00).\n')
L.append('| object | review midpoint | sweep base lib (n) | sweep base scan | newest perc lib | newest perc scan | newest lib excl. ep23 | newest scan excl. ep23 | canonical perc lib (n) | e2s lib | reference lib | reference scan |')
L.append('|---|---|---|---|---|---|---|---|---|---|---|---|')
for o in MIDPOINT:
    def c(t, show_n=False):
        v = T[t].get(o)
        return '' if v is None else (f"{v['mean']:.3f} ({v['n']})" if show_n else f"{v['mean']:.3f}")
    L.append(f"| {o} | {MIDPOINT[o]} | {c('sweep_lib', True)} | {c('sweep_scan')} | {c('newest_lib')} | {c('newest_scan')} | "
             f"{c('newest_lib_excl_identity_fail')} | {c('newest_scan_excl_identity_fail')} | "
             f"{c('perc_can_lib', True)} | {c('e2s_can_lib')} | {c('ref_lib')} | {c('ref_scan')} |")

# ---- 4. stale refsweep pairs
L.append('\n### Stale 20 Oct refsweep pairs (public-scan templates; scored with the scans)\n')
L.append('| ep | object | perc | ref | ref - perc |')
L.append('|---|---|---|---|---|')
stf = []
for ep in STALE:
    s = R['stale'][ep]
    if s['perc'] is None or s['ref'] is None:
        continue
    for n in s['perc']['objects'] + ['(scene)']:
        k = None if n == '(scene)' else n
        pv, rv = g(s, 'perc', k), g(s, 'ref', k)
        L.append(f'| {ep} | {n} | {f4(pv)} | {f4(rv)} | {f4(rv - pv)} |')
        if rv < pv - 0.01:
            stf.append(dict(kind='stale_ref_below_perc', ep=ep, object=n, perc=pv, ref=rv))
R['flags_stale'] = stf

# ---- 5. multiplicative model check on the rollouts: sim AUC vs sim_vs_ref x ref AUC
L.append('\n### Rollout r1: sim AUC vs sim_vs_ref x reference AUC (the hidden-loss model)\n')
L.append('| ep | sim lib | sim_vs_ref (box, r1) | ref lib | sim_vs_ref x ref lib | static floor lib |')
L.append('|---|---|---|---|---|---|')
C = json.load(open('/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck/work/canonical_refs.json'))['episodes']
mm = []
for e in C:
    ep = e['ep']
    if ep not in CAN or R['chain'][ep]['sim_lib'] is None:
        continue
    sfile = f"/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck/store/{e['results_dir']}/summary.json"
    svr = None
    if os.path.exists(sfile):
        sm = json.load(open(sfile))
        svr = next((x['sim_vs_ref'] for x in sm.get('rollouts', []) if x.get('rollout') == 'r1'), None)
    r = R['chain'][ep]; sl, rl, fl = r['sim_lib']['AUC'], r['ref_lib']['AUC'], r['floor_lib']['AUC']
    L.append(f'| {ep} | {sl:.3f} | {f4(svr)} | {rl:.3f} | {f4(None if svr is None else svr * rl)} | {fl:.3f} |')
    mm.append(dict(ep=ep, sim_lib=sl, sim_vs_ref=svr, ref_lib=rl, floor_lib=fl))
R['model_check'] = mm

# ---- 6. per-object registration attribution (hyb_jobs.py: one object with our mesh, the other with its scan)
HYB = {11: ['blue_cup', 'beige_cup'], 12: ['blue_cup', 'plastic_dish_rack'], 21: ['blue_cup', 'water_pitcher'],
       31: ['mini_sweeper', 'plastic_dish_rack']}
L.append('\n### Registration cost split by object (perception path / final reference; AUC per object)\n')
L.append('Slot 0 is the first object listed: the kit aligns the scene on its frame-0 position.\n')
L.append('| ep | path | object | all scans | only slot-0 object ours | only slot-1 object ours | all ours |')
L.append('|---|---|---|---|---|---|---|')
R['hybrid'] = {}
for ep, objs in HYB.items():
    for src in ('perc', 'proc'):
        base = load(f'can_ep{ep}_perc_scan') if src == 'perc' else load(f'can_ep{ep}_res_scan', 'reference')
        allo = load(f'can_ep{ep}_{src}_lib')
        h0, h1 = load(f'hyb_ep{ep}_{src}_{objs[0]}_ours'), load(f'hyb_ep{ep}_{src}_{objs[1]}_ours')
        if None in (base, allo, h0, h1):
            continue
        for n in objs:
            L.append(f"| {ep} | {'perception' if src == 'perc' else 'reference'} | {n} | {base['obj'][n]:.3f} | {h0['obj'][n]:.3f} | {h1['obj'][n]:.3f} | {allo['obj'][n]:.3f} |")
        R['hybrid'][f'{ep}_{src}'] = dict(scan=base['obj'], only0=h0['obj'], only1=h1['obj'], ours=allo['obj'], objects=objs)

# ---- 7. frame-level diagnosis of the links (diag.py)
DD = os.path.join(os.path.dirname(SD.rstrip('/')), 'diag')
L.append('\n### Frame-level diagnosis of the flagged links (diag.py)\n')
L.append('dAUC = B - A; trans/rot = the change with only B\'s position (orientation) applied; change = B - A in the '
         'kit-aligned frame; dz err = mean vertical error of the anchor point vs mocap (A -> B).\n')
L.append('| link | ep | object | meshes | dAUC | frame-0 share | trans only | rot only | frames worse / better | change dz cm (mean) | change rot deg (mean / max) | dz err A -> B cm | worst segment |')
L.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
R['diag'] = {}
for f in sorted(os.listdir(DD)) if os.path.isdir(DD) else []:
    if not f.endswith('.json'):
        continue
    d = json.load(open(f'{DD}/{f}')); tag = f[:-5]; R['diag'][tag] = d
    link = tag.split('_')[0]; ep = d['episode']
    ms = 'scan->ours' if link == 'reg' else ('ours' if 'library' in d.get('meshes_A', '') else 'scan')
    for n, o in d['per_object'].items():
        if abs(o['dAUC']) < 0.005:
            continue
        sg = o['segments_worse'][0] if o['dAUC'] < 0 and o['segments_worse'] else (o['segments_better'][0] if o['segments_better'] else None)
        sgs = '' if sg is None else f"f{sg['frames'][0]}-{sg['frames'][1]} ({sg['dAUC']:+.3f})"
        c = o['change_B_minus_A']
        L.append(f"| {link} | {ep} | {n} | {ms} | {o['dAUC']:+.3f} | {o['dAUC_frame0']:+.4f} | {o['dAUC_translation_only']:+.3f} | "
                 f"{o['dAUC_rotation_only']:+.3f} | {o['frames_worse']} / {o['frames_better']} | {c['dz_cm_mean']:+.2f} | "
                 f"{c['drot_deg_mean']:.2f} / {c['drot_deg_max']:.2f} | {o['error_A']['dz_cm_mean']:+.2f} -> {o['error_B']['dz_cm_mean']:+.2f} | {sgs} |")

L.append('\n### Flags\n')
for f_ in flags + sflags + stf:
    L.append('- ' + json.dumps(f_))
open(f'{OUT}/tables.md', 'w').write('\n'.join(L) + '\n')
json.dump(R, open(f'{OUT}/results.json', 'w'), indent=1, default=str)
print('\n'.join(L))
