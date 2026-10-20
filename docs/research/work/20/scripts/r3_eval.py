"""DIG 20 Stage C round 3: final GT-free pipeline evaluation.
Mask per clip: round-3 flat-object mask (out/c3, planks + spoon) when it exists, else the re-run template mask (out/c2).
Frozen MC detector (no retuning). Confidence flag (inference-safe, public priors only):
  template classes: final score < 0.5 x the public class median (leave-own-episode-out) OR colour distance dcol > 12;
  flat classes: no footprint candidate with size score < 0.5, or a twin task with < 2 such candidates.
A flagged clip goes to the static-end fallback (no image window).
Public (analysis only, after inference): onset error vs raw / robust GT perturbation, anchor bias of the window.
Eval: window vs the note-15 viewing reference (approximate, +-8 f; design check only).
usage: r3_eval.py -> out/c3/final_eval.json"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import c_lib as L
from c_eval import window_bias, gt
O2 = f'{L.ROOT}/work/20/out/c2'; O3 = f'{L.ROOT}/work/20/out/c3'
REF = json.load(open(f'{O2}/eval_view_ref.json'))
ST = {r['ep']: r for r in json.load(open(f'{L.OUT}/eval2_MC_A120_T2_L10_m3.json'))}
PUB = L.PUB + [45]
FAM = {'blue_cup': 'cup', 'beige_cup': 'cup'}     # class family for the score prior (no public beige_cup slot 0)


def src(key):
    return O3 if os.path.exists(f'{O3}/run_{key}.npz') else O2


def pub_finals(name, excl):
    v = []
    for ep in PUB:
        if ep == excl: continue
        f = f'{O2}/pose0_p{ep}.json'
        if not os.path.exists(f): continue
        m = json.load(open(f))
        if FAM.get(m['name'], m['name']) == FAM.get(name, name) and 'peaks' in m: v.append(m['peaks'][0]['final'])
    return v


def conf(key):
    o = src(key); m = json.load(open(f'{o}/pose0_{key}.json'))
    if o == O3:
        good = [c for c in m['cands'] if not c['ego'] and c['size_score'] < 0.5]
        twin = m['name'].startswith('wooden_piece')
        ok = len(good) >= (2 if twin else 1)
        return dict(src='flat', ok=ok, why=f"{len(good)} good footprints (size score {m['pick']['size_score']:.2f})" if m['pick'] else 'no pick')
    p = m['peaks'][0]; ep = int(key[1:]); v = pub_finals(m['name'], ep if key[0] == 'p' else None)
    thr = 0.5 * float(np.median(v)) if v else 0.0
    ok = p['final'] >= thr and p['dcol'] <= 12
    return dict(src='template', ok=bool(ok), why=f"final {p['final']:.2f} vs thr {thr:.2f} (n{len(v)}), dcol {p['dcol']:.0f}")


R = []
for ep in PUB:
    key = f'p{ep}'; o = src(key); d = json.loads(str(np.load(f'{o}/run_{key}.npz')['dec'])); g = gt(ep); c = conf(key)
    end = d['window_end_row']; wb = window_bias(ep, min(end, g['n'] - 1))
    row = dict(key=key, name=g['name'], mask=os.path.basename(o), conf=c, **d, pert=g['pert'], pert_r=g['pert_r'], on=g['on'],
               e_raw=d['c_bc'] - g['pert'], e_rob=d['c_bc'] - g['pert_r'], late_raw=end >= g['pert'], late_rob=end >= g['pert_r'],
               n_win=wb['n'], dt=wb['dt'], dR=wb['dR'], shift=wb['shift'])
    R.append(row)
    print(f"{key:4s} {g['name'][:12]:12s} {row['mask']:2s} conf {'ok ' if c['ok'] else 'FLAG'} ({c['why']}) | C a{d['C_a']} M a{d['M_a']} end {end:3d} | "
          f"pert {g['pert']}/{g['pert_r']} | err raw {row['e_raw']:+4d} rob {row['e_rob']:+4d}{' LATE' if row['late_rob'] else ''} | n {wb['n']:3d} dt {wb['dt']:.2f} dR {wb['dR']:.2f}")


def stats(rows, tag):
    er = np.array([r['e_raw'] for r in rows]); eb = np.array([r['e_rob'] for r in rows]); dR = np.array([r['dR'] for r in rows]); dt = np.array([r['dt'] for r in rows])
    s = dict(n=len(rows), raw_med=float(np.median(er)), raw_p10=float(np.percentile(er, 10)), raw_p90=float(np.percentile(er, 90)),
             raw_min=int(er.min()), raw_max=int(er.max()), rob_med=float(np.median(eb)), rob_p10=float(np.percentile(eb, 10)),
             rob_p90=float(np.percentile(eb, 90)), within2_raw=int((np.abs(er) <= 2).sum()),
             late_raw=int(sum(r['late_raw'] for r in rows)), late_rob=int(sum(r['late_rob'] for r in rows)),
             empty=int(sum(r['window_end_row'] < 0 for r in rows)), win_med=float(np.median([r['n_win'] for r in rows])),
             dt_med=float(np.median(dt)), dt_p90=float(np.percentile(dt, 90)), dt_max=float(dt.max()),
             dR_med=float(np.median(dR)), dR_p90=float(np.percentile(dR, 90)), dR_max=float(dR.max()),
             flagged=[r['key'] for r in rows if not r['conf']['ok']])
    print(f"== {tag}: n {s['n']} | onset err raw median {s['raw_med']:+.0f} p10/p90 {s['raw_p10']:+.0f}/{s['raw_p90']:+.0f} range [{s['raw_min']},{s['raw_max']}] "
          f"(|e|<=2: {s['within2_raw']}); robust median {s['rob_med']:+.0f} p10/p90 {s['rob_p10']:+.0f}/{s['rob_p90']:+.0f} | late raw/robust {s['late_raw']}/{s['late_rob']} "
          f"empty {s['empty']} | window median {s['win_med']:.0f} | dt {s['dt_med']:.2f}/{s['dt_p90']:.2f}/{s['dt_max']:.2f} mm | dR {s['dR_med']:.2f}/{s['dR_p90']:.2f}/{s['dR_max']:.2f} deg | flagged {s['flagged']}")
    return s


S = dict(pub20=stats(R, 'final pipeline, public 20 (19 + p45)'), pub19=stats([r for r in R if r['key'] != 'p45'], 'final pipeline, Stage C 19'))
E = []
for ep in L.EV:
    key = f'e{ep}'; o = src(key); d = json.loads(str(np.load(f'{o}/run_{key}.npz')['dec'])); ref = REF[key]; c = conf(key)
    m0 = ref['motion'][0] if ref['motion'] else None
    late = m0 is not None and d['c_a'] - 3 > m0 + 8
    fl = ('EMPTY' if d['empty'] else '') + (' LATE?' if late else '') + ('' if c['ok'] else ' CONF-FLAG')
    E.append(dict(key=key, slot0=ref['slot0'], mask=os.path.basename(o), conf=c, **d, view_contact=ref['contact'], view_motion=ref['motion'], late=late))
    print(f"{key:4s} {ref['slot0'][:12]:12s} {os.path.basename(o)} conf {'ok ' if c['ok'] else 'FLAG'} ({c['why']}) | C a{d['C_a']} M a{d['M_a']} -> a{d['c_a']} end row {d['window_end_row']} "
          f"| view contact {ref['contact']} motion {ref['motion']} |{fl}")
ends = np.array([r['window_end_row'] for r in E])
print(f"eval: n {len(E)}; empty {int((ends < 0).sum())}; late? {[r['key'] for r in E if r['late']]}; flagged {[r['key'] for r in E if not r['conf']['ok']]}; "
      f"window end median {np.median(ends[ends >= 0]):.0f}")
json.dump(dict(public=R, stats=S, evaluation=E), open(f'{O3}/final_eval.json', 'w'), indent=1, default=float)
