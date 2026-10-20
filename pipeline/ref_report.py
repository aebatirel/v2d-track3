"""Per-episode health report of the reference pipeline (perception -> hands -> mkref) before any training.

Reads, for each public episode, /content/<perc>/epN/result.json (perception scored against mocap after inference),
/content/refs/<perc>/epN/hands_log.json, ref_summary.json and mkref_log.txt, and flags what would make training
pointless: no support plane, failed FlashCHORD validation, big wrist jumps, no hand-object contact, poor tracking.
Usage: python ref_report.py [perc2] [EP ...]   -> prints a table, writes /content/results/ref_report_<perc>.json
"""
import json, os, re, sys

PERC = sys.argv[1] if len(sys.argv) > 1 else 'perc2'
PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
EPS = [int(e) for e in sys.argv[2:]] or PUBLIC


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


rows = []
for ep in EPS:
    P, R = f'/content/{PERC}/ep{ep}', f'/content/refs/{PERC}/ep{ep}'
    r = dict(ep=ep)
    res = load(f'{P}/result.json')
    if res:
        vo = res.get('vo') or {}
        r.update(objects=res.get('objects'), perc_auc=vo.get('AUC'), perc_mp=vo.get('MP_SR'),
                 perc_obj={k: round(v, 3) for k, v in (vo.get('per_obj_AUC') or {}).items()})
    hl = load(f'{R}/hands_log.json')
    if hl:
        r.update(hand_frames=round(hl['frames_with_hand'] / hl['T'], 2), two_hand_frames=round(hl['frames_two_hands'] / hl['T'], 2),
                 hand_swap=hl.get('swap'))
    rs = load(f'{R}/ref_summary.json')
    log = open(f'{R}/mkref_log.txt').read() if os.path.exists(f'{R}/mkref_log.txt') else ''
    m = re.search(r'no support plane under the objects: [^\n]*', log)
    if m:
        r['fail'] = m.group(0)[:120]
    elif rs is None and log:
        r['fail'] = 'mkref: ' + log.strip().splitlines()[-1][:120]
    m = re.search(r'table plane candidates[^\[]*(\[.*\])', log)
    if m:
        r['planes'] = m.group(1)[:200]
    if rs:
        t = rs.get('table', {})
        r.update(bottoms_cm=[round(x, 1) for x in t.get('bottoms_cm', [])], valid=rs.get('validation', {}).get('ok'),
                 wrist_max_step_cm={s: round(w['max_step_cm'], 1) for s, w in rs.get('wrist', {}).items()},
                 contact_frac={s: round(c['frames_with_contact'], 2) for s, c in rs.get('contacts', {}).items()})
        ik = rs.get('ik', {})
        r['tip_err_mm'] = {s: round(sorted(v['median_mm'] for k, v in d.items() if 'tip' in k)[len([k for k in d if 'tip' in k]) // 2], 1)
                           for s, d in ik.items() if d}
    flags = []
    if r.get('fail'):
        flags.append('NO-REF')
    if r.get('valid') is False:
        flags.append('INVALID')
    if (r.get('perc_auc') or 1) < 0.7:
        flags.append('TRACKING')
    if any(v > 8 for v in (r.get('wrist_max_step_cm') or {}).values()):
        flags.append('WRIST-JUMP')
    if r.get('contact_frac') and max(r['contact_frac'].values()) < 0.1:
        flags.append('NO-CONTACT')
    r['flags'] = flags
    rows.append(r)

for r in rows:
    print(f"ep{r['ep']:>2} perc {r.get('perc_auc') if r.get('perc_auc') is None else round(r['perc_auc'], 3)!s:>6} "
          f"hands {r.get('hand_frames')!s:>4} bottoms {r.get('bottoms_cm')} valid {r.get('valid')} "
          f"wrist {r.get('wrist_max_step_cm')} contact {r.get('contact_frac')} tips {r.get('tip_err_mm')} "
          f"{' '.join(r['flags'])} {r.get('fail', '')}")
os.makedirs('/content/results', exist_ok=True)
json.dump(rows, open(f'/content/results/ref_report_{PERC}.json', 'w'), indent=1)
