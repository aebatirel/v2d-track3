#!/usr/bin/env python
"""T3 one-shot scoring wrapper around scripts/mesh_metric.py (DIAGNOSTIC [D]: reads the public scans).

Run ONLY after PREREG.md (with the sha256 of every mesh listed in the manifest) is committed and pushed.
One record per mesh; a mesh whose sha (mesh_metric's sha1[:16]) is already in OUT is never scored again.

Seeds: mesh_metric.evaluate's default (every eval (episode, slot) seed of the object + its default extra seeds
11,22,..., max(2, 6 - n_eval) of them). For mini_sweeper, wooden_piece_1 and wooden_piece_2 the extra seeds are
1001..1030 and ALL 30 are used (min_extra=30): the CLI's --seeds would only use max(2, 6 - n_eval) of them, which is
why this wrapper calls evaluate() directly. flips_extra = flips over the 30 extra seeds.

Usage: score.py MANIFEST.tsv OUT.jsonl      (manifest lines: label<TAB>object<TAB>path)
"""
import importlib.util, json, os, sys

MM = '/home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts/mesh_metric.py'
FLIP30 = ('mini_sweeper', 'wooden_piece_1', 'wooden_piece_2')


def main():
    man, out = sys.argv[1], sys.argv[2]
    spec = importlib.util.spec_from_file_location('mesh_metric', MM)
    mm = importlib.util.module_from_spec(spec); spec.loader.exec_module(mm)
    done = set()
    if os.path.exists(out):
        for line in open(out):
            r = json.loads(line)
            done.add(r.get('sha'))
    items = [l.rstrip('\n').split('\t')[:3] for l in open(man) if l.strip() and not l.startswith('#')]
    for i, (label, name, path) in enumerate(items, 1):
        if mm.sha(path) in done:
            print(f'[{i}/{len(items)}] {label}: already scored, skipped', flush=True)
            continue
        kw = {}
        if name in FLIP30:
            kw = dict(seeds_extra=tuple(range(1001, 1031)), min_extra=30)
        try:
            rec = mm.evaluate(label, name, path, **kw)
        except Exception as err:                                       # noqa: BLE001
            rec = dict(label=label, object=name, path=path, sha=mm.sha(path), error=repr(err))
        if 'seeds' in rec:
            ex = [r for r in rec['seeds'] if r['ep'] is None]
            rec['n_extra'] = len(ex)
            rec['flips_extra'] = int(sum(r['flip'] for r in ex))
        with open(out, 'a') as fh:
            fh.write(json.dumps(rec) + '\n')
        print(f'[{i}/{len(items)}] {label} cdo_eval {rec.get("cdo_eval")} add_med {rec.get("add_med")} '
              f'flips {rec.get("flips_all")}/{rec.get("n_seeds")} extra {rec.get("flips_extra")}/{rec.get("n_extra")} '
              f'({rec.get("secs")} s) {rec.get("error", "")}', flush=True)


if __name__ == '__main__':
    main()
