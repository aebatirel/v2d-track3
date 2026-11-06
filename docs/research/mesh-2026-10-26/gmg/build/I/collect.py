"""Copy the small BI2 results of a dev run into build/I/results/ (JSON stripped of per-voxel arrays) and the delivered
r0 simulator folders into build/I/sim_r0/ (dev tier: pieces, visual GLB, props, manifest).
  python collect.py RUN TAG_DIR(ep24-evalsem ...) DEST_NAME"""
import json, os, shutil, sys

run, tag, dest = sys.argv[1:4]
here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(run, 'interlock', 'public', tag)
out = os.path.join(here, 'results', dest)
os.makedirs(out, exist_ok=True)


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in ('nmv', 'nmf', 'nmv_sub', 'nmf_sub', 'notches', 'series',
                                                                 'per_frame_t_mm', 'log')}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


for f in sorted(os.listdir(src)):
    if f.endswith('.json'):
        d = json.load(open(os.path.join(src, f)))
        if f.startswith('overlap_') or f.startswith('physcheck'):
            keep = d                                   # per-frame series are small and plotted
        else:
            keep = strip(d)
        json.dump(keep, open(os.path.join(out, f), 'w'), indent=1)
sim = os.path.join(run, 'sim', 'public', tag, 'r0')
if os.path.isdir(sim):
    sd = os.path.join(here, 'sim_r0', dest)
    if os.path.exists(sd):
        shutil.rmtree(sd)
    shutil.copytree(sim, sd)
print('copied', src, '->', out)
