"""PREREG B.10 (build step B3, dev only, $0): the 104 gen-probe meshes through the M10 remesh.

Reads the scoring manifest of the 29 Oct generator probe (`results/gen-probe/score_manifest.tsv`: tag, object, mesh
path, model; paths only, no score file is opened) and every mesh it names (role x0_pool, dev only: the probe's crops
were seeded with library_v3, so these meshes never enter a clean run). Each mesh goes through remesh.watertight
(pitch 1.5 mm, largest component, fit_budget 4000) and pack.pack (GLB, the gmg's own copy of the kit decode, V1).
B.10 passes if at least 100 of the 104 are watertight after the decode.

Outputs in RUN/b10/: results.jsonl (one record per mesh, resumable), summary.json, <model>/<tag>.glb (packed).
Nothing is scored; no scan, mocap or library file is read.

Usage (dev only):
  GMG_MODE=dev python -m gmg.tools.b10_remesh --run RUN [--manifest TSV] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from gmg import guard, remesh as RM, pack as PK  # noqa: E402

T0 = time.time()
PASS_MIN = 100          # PREREG B.10: at least 100 of 104


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def read_manifest(path):
    rp = guard.open_input(path, 'x0_pool')
    rows = []
    with open(rp) as f:
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) < 4:
                continue
            rows.append(dict(tag=p[0], obj=p[1], path=p[2].replace('<scratchpad>', guard.CFG['data']), model=p[3]))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run', required=True)
    ap.add_argument('--manifest', default=os.path.join(guard.CFG['mr'], 'results', 'gen-probe', 'score_manifest.tsv'))
    ap.add_argument('--limit', type=int, default=None)
    a = ap.parse_args()
    if guard.mode() != 'dev':
        raise SystemExit('b10_remesh: dev only (GMG_MODE=dev): the gen-probe meshes are role x0_pool')
    import trimesh
    guard.set_run(a.run)
    start = dict(start_commit=guard._git('rev-parse', 'HEAD'))
    out = os.path.join(a.run, 'b10')
    os.makedirs(out, exist_ok=True)
    RM.consts()
    rows = read_manifest(a.manifest)
    if a.limit:
        rows = rows[:a.limit]
    res_path = os.path.join(out, 'results.jsonl')
    done = {}
    if os.path.exists(res_path):
        with open(guard.open_input(res_path, 'own')) as f:
            for line in f:
                r = json.loads(line)
                done[r['tag']] = r
    with open(res_path, 'a') as fo:
        for i, r in enumerate(rows):
            if r['tag'] in done:
                continue
            t = time.time()
            rec = dict(tag=r['tag'], obj=r['obj'], model=r['model'], src=os.path.relpath(r['path'], guard.CFG['data']))
            try:
                rp = guard.open_input(r['path'], 'x0_pool')
                rec['src_sha256'] = guard._sha256(rp)
                m = trimesh.load(rp, force='mesh', process=False)
                rec['raw'] = dict(faces=int(len(m.faces)), vertices=int(len(m.vertices)),
                                  watertight=bool(trimesh.Trimesh(m.vertices, m.faces, process=True).is_watertight))
                mb, info = RM.watertight(m)
                rec['remesh'] = info
                glb = os.path.join(out, r['model'], r['tag'].replace('/', '_') + '.glb')
                _, pinfo = PK.pack(mb, glb)
                guard.register_output(glb)
                rec['pack'] = dict((k, pinfo.get(k)) for k in ('faces', 'vertices', 'watertight_packed', 'sha256'))
                rec['v1'] = pinfo['v1']
                rec['watertight_after_decode'] = bool(pinfo['v1']['watertight'])
            except Exception as e:                                           # noqa: BLE001
                if isinstance(e, guard.GuardError):
                    raise
                rec['error'] = f'{type(e).__name__}: {e}'
                rec['watertight_after_decode'] = False
            rec['sec'] = round(time.time() - t, 1)
            fo.write(json.dumps(rec, default=float) + '\n')
            fo.flush()
            done[r['tag']] = rec
            ri = rec.get('remesh', {})
            log(f"{i + 1}/{len(rows)} {r['tag']}: raw wt {rec.get('raw', {}).get('watertight')} -> decode wt "
                f"{rec['watertight_after_decode']} faces {rec.get('pack', {}).get('faces')} cov {ri.get('coverage')} "
                f"comp {ri.get('components')} flags {ri.get('flags')} ({rec['sec']} s){' ' + rec['error'] if 'error' in rec else ''}")
    guard.register_output(res_path)
    recs = [done[r['tag']] for r in rows if r['tag'] in done]
    by_model = {}
    for r in recs:
        d = by_model.setdefault(r['model'], dict(n=0, raw_watertight=0, watertight_after_decode=0, thin_union=0))
        d['n'] += 1
        d['raw_watertight'] += int(bool(r.get('raw', {}).get('watertight')))
        d['watertight_after_decode'] += int(r['watertight_after_decode'])
        d['thin_union'] += int('thin_union' in r.get('remesh', {}).get('flags', []))
    n_ok = sum(int(r['watertight_after_decode']) for r in recs)
    cov = sorted(r['remesh']['coverage'] for r in recs if 'remesh' in r)
    summ = dict(prereg='B.10', n=len(recs), n_manifest=len(rows), watertight_after_decode=n_ok, pass_min=PASS_MIN,
                pass_=bool(len(recs) == 104 and n_ok >= PASS_MIN) if not a.limit else None,
                by_model=by_model, failures=[dict(tag=r['tag'], error=r.get('error'), v1=r.get('v1'))
                                             for r in recs if not r['watertight_after_decode']],
                coverage=dict(min=cov[0] if cov else None, median=cov[len(cov) // 2] if cov else None,
                              below_0_9=sum(c < 0.9 for c in cov)),
                faces_max=max((r.get('pack', {}).get('faces') or 0) for r in recs) if recs else None,
                sec_total=round(sum(r['sec'] for r in recs), 1))
    sp = os.path.join(out, 'summary.json')
    with open(sp, 'w') as f:
        json.dump(summ, f, indent=1)
    guard.register_output(sp)
    guard.write_manifest(os.path.join(a.run, 'manifest.json'), extra=dict(step='B3', prereg='B.10', pass_=summ['pass_'],
                                                                         **start))
    log(f"B.10: {n_ok}/{len(recs)} watertight after decode -> {'PASS' if summ['pass_'] else summ['pass_']}")


if __name__ == '__main__':
    main()
