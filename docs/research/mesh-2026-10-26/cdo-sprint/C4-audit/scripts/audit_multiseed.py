"""C4 multi-seed registration audit (PREREG.md section 2). Diagnostic [D]: public scans stand in for the hidden scans.

For every mesh in candidates.json (in file order), one mesh_metric.evaluate() run with the eval roster EMPTIED and
50 seeds 3001..3050, so no eval seed is used. Generated candidates (needs_place) are first placed in the library_v3
frame with the GT-free C1/T2 place.py, and the placed copy is audited. One run per mesh. A finished index is never
re-run; a crashed one is re-run once.

Usage: MESH_SCR=<scratch> audit_multiseed.py CANDIDATES.json OUT_DIR [--only ROLE[,ROLE]] [--workers 4]
"""
import argparse, json, os, subprocess, sys, time, traceback
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'docs/research/mesh-2026-10-26/scripts'))
PLACE = os.path.join(REPO, 'docs/research/mesh-2026-10-26/cdo-sprint/C1/T2-probe-picks/scripts/place.py')
SEEDS = tuple(range(3001, 3051))


def summarise(rec):
    import numpy as np
    rows = rec['seeds']
    c = np.array([r['cdo_cm'] for r in rows]); a = np.array([r['anchor_mm'] for r in rows])
    rot = np.array([r['rot_deg'] for r in rows]); add = np.array([r['add_mm'] for r in rows])
    return dict(n=len(rows), cdo_med=round(float(np.median(c)), 4), cdo_mean=round(float(c.mean()), 4),
                flip=round(float((rot > 90).mean()), 3), w30=round(float((rot > 30).mean()), 3),
                anc_med=round(float(np.median(a)), 2), anc_p90=round(float(np.percentile(a, 90)), 2),
                rot_med=round(float(np.median(rot)), 2), rot_p90=round(float(np.percentile(rot, 90)), 2),
                add_med=round(float(np.median(add)), 2), add_p90=round(float(np.percentile(add, 90)), 2),
                amb_mm=rec.get('amb_mm'), amb_floor_mm=rec.get('amb_floor_mm'), amb_rot=rec.get('amb_rot'))


def work(args):
    i, item, out = args
    dst = os.path.join(out, 'raw', f'{i:03d}.json')
    if os.path.exists(dst):
        return i, 'done-before'
    import mesh_metric as MM
    MM.ROSTER = {}                                   # no eval seeds (PREREG s2)
    path = item['path']
    t0 = time.time()
    for attempt in (1, 2):
        try:
            if item.get('needs_place'):
                stem = os.path.join(out, 'place', f'{i:03d}_{item["object"]}')
                if not os.path.exists(stem + '.glb'):
                    lib = os.path.join(REPO, 'meshes/library_v3', item['object'] + '.glb')
                    subprocess.run([sys.executable, '-I', PLACE, item['object'], path, lib, stem], check=True,
                                   stdout=subprocess.DEVNULL, cwd=os.path.join(out, 'place'))
                path = stem + '.glb'
            rec = MM.evaluate(item['label'], item['object'], path, group='c4_audit', seeds_extra=SEEDS,
                              min_seeds=0, min_extra=len(SEEDS))
            rec['c4'] = dict(index=i, role=item['role'], source=item['path'], source_md5=item['md5'],
                             audited_path=path, attempt=attempt, summary=summarise(rec))
            with open(dst + '.part', 'w') as f:
                json.dump(rec, f)
            os.replace(dst + '.part', dst)
            return i, f'ok {time.time() - t0:.0f}s'
        except Exception:
            err = traceback.format_exc()
            with open(os.path.join(out, 'raw', f'{i:03d}.err{attempt}'), 'w') as f:
                f.write(err)
    return i, 'FAILED twice'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cands'); ap.add_argument('out')
    ap.add_argument('--only', default='')
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, 'raw'), exist_ok=True)
    os.makedirs(os.path.join(a.out, 'place'), exist_ok=True)
    plan = json.load(open(a.cands))
    roles = set(a.only.split(',')) if a.only else None
    jobs = [(i, it, a.out) for i, it in enumerate(plan) if roles is None or it['role'] in roles]
    print(time.strftime('%FT%TZ', time.gmtime()), f'{len(jobs)} meshes, {a.workers} workers', flush=True)
    with Pool(a.workers) as pool:
        for i, msg in pool.imap_unordered(work, jobs):
            print(time.strftime('%FT%TZ', time.gmtime()), i, plan[i]['label'], msg, flush=True)


if __name__ == '__main__':
    main()
