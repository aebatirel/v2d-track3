"""Pack-side check of D-arm candidates (2026-10-31, pack 9b; docs/research/work/pack9b-20261031/PREREG.md section 3). Run by
ops/jobs/pack_eval.sh (DR_EPS, opt-in) right before the kit evaluator, and by ops/jobs/h5_reeval.sh before draws 2..N.
The kit evaluator rebuilds each scene from the checkpoint's saved config (task.parquet -> object_urdf_paths -> the
URDF verbatim when it is a file, otherwise silently re-rooted onto FlashCHORD's own assets; tools/mass_pack_check.py
docstring). For every episode about to be evaluated (CHECKPOINTS) this follows that chain (mass_pack_check.chain) and
requires: every URDF resolves verbatim and carries the 0.3 kg placeholder (no masses anywhere in this arm); for each
--dr-eps episode with a --table row: the reference's md5 and fingerprint are the packed reference's (the D arm trains
on a byte copy), where the table names collision pieces (eval 25: meshes/carve/ev25) each such object has one
<collision> per piece, and the checkpoint is NOT the table's packed checkpoint (sha256; else the PICK did not take).
A --dr-eps episode that is not evaluated here (kept) or not in --all is a failure. No ground truth is read.
Exit 1 on any failure. Usage:
  dr_pack_check.py --checkpoints CK_EVAL.json [--all CK_ALL.json] --dr-eps "14 16 25 30 33" --table packed_refs.json
                   [--content /content] --out OUT.json
"""
import argparse, glob, hashlib, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from mass_arm import PLACEHOLDER                    # noqa: E402
from mass_pack_check import chain                   # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--checkpoints', required=True); ap.add_argument('--all', default='')
    ap.add_argument('--dr-eps', required=True); ap.add_argument('--table', required=True)
    ap.add_argument('--content', default='/content'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ev = json.load(open(a.checkpoints)); allc = json.load(open(a.all)) if a.all else ev
    tab = json.load(open(a.table))['episodes']
    dr = {str(int(x)) for x in a.dr_eps.split()}; fails, rows = [], {}
    if not dr:
        fails.append('DR_EPS is empty')
    for e in sorted(dr - set(allc), key=int):
        fails.append(f'ep{e}: in DR_EPS but not in the pack\'s checkpoints')
    for e in sorted(dr & set(allc) - set(ev), key=int):
        fails.append(f'ep{e}: in DR_EPS but not evaluated here (its D checkpoint matched a kept rollout?)')
    for e in sorted(dr - set(tab), key=int):
        fails.append(f'ep{e}: in DR_EPS but not in the table {a.table}')
    for e in sorted(ev, key=int):
        row = rows[e] = dict(checkpoint=ev[e], dr_candidate=e in dr)
        try:
            rp, fp, m5, loaded = chain(ev[e], a.content)
        except Exception as x:
            row['error'] = f'{type(x).__name__}: {str(x)[:200]}'; fails.append(f'ep{e}: {row["error"]}'); continue
        row.update(reference=rp, traj_fingerprint=fp, reference_md5=m5, loaded=loaded,
                   checkpoint_sha256=hashlib.sha256(open(ev[e], 'rb').read()).hexdigest())
        for n, v in loaded.items():
            if v['mass'] is None:
                fails.append(f'ep{e}: {n}: {v["urdf"]} {v["how"]}'); continue
            if abs(v['mass'] - PLACEHOLDER) > 1e-9:
                fails.append(f'ep{e}: {n} would be evaluated with {v["mass"]} kg ({v["urdf"]}); this arm keeps {PLACEHOLDER} kg')
        if e in dr and e in tab:
            T = tab[e]
            if fp != T['traj_fingerprint'] or m5 != T['md5']:
                fails.append(f'ep{e}: reference {m5} / {fp} is not the packed reference {T["md5"]} / {T["traj_fingerprint"]}')
            if row['checkpoint_sha256'] == T.get('packed_sha256'):
                fails.append(f'ep{e}: the checkpoint to evaluate is the packed one ({T["packed_sha256"][:12]}): the D PICK did not take')
            if T.get('pieces'):
                for n, v in loaded.items():
                    k = len(glob.glob(os.path.join(REPO, T['pieces'], n, 'piece_*.obj')))
                    c = len(re.findall(r'<collision>', open(v['urdf']).read())) if v['mass'] is not None else None
                    v['collisions'] = c
                    if k and c != k:
                        fails.append(f'ep{e}: {n} has {c} collision pieces ({v["urdf"]}), it trained with the {k} of {T["pieces"]}')
    out = dict(ok=not fails, failures=fails, dr_eps=sorted(dr, key=int), evaluated=sorted(ev, key=int), episodes=rows)
    json.dump(out, open(a.out, 'w'), indent=1)
    print(('dr_pack_check: OK' if not fails else f'dr_pack_check: REFUSED ({len(fails)}): ' + ' | '.join(fails[:6]))
          + f' :: evaluated {sorted(ev, key=int)}, D candidates {sorted(dr & set(ev), key=int)} :: '
          + '; '.join(f'ep{e} ' + ','.join(f'{n} {v["mass"]}' for n, v in r.get('loaded', {}).items())
                      + (f' sha {r["checkpoint_sha256"][:12]}' if 'checkpoint_sha256' in r else '') for e, r in rows.items()))
    sys.exit(0 if not fails else 1)


if __name__ == '__main__':
    main()
