"""Pack-side mass check (2026-10-31, masses eval retrain; docs/research/work/masses-eval-20261031/BUILD.md). Run by
ops/jobs/pack_eval.sh (MASS_EPS) right before the kit evaluator, and by ops/jobs/h5_reeval.sh before draws 2..N.

The kit evaluator (examples/run_policy_evaluation.py -> evaluate_policy.py -> evaluation/harness.py evaluate_checkpoint)
rebuilds each episode's scene from the checkpoint's saved config: task.parquet (Path(...).resolve(), then
data/parquet.py resolve_parquet: a file, or a folder with exactly one .parquet) -> object_urdf_paths ->
assets/registry.py resolve_asset_path: the stored path VERBATIM when it is a file, otherwise re-rooted onto FlashCHORD's
own assets (a silent swap) -> scene/objects.py add_urdf with the URDF inertials. So an episode is evaluated with the
masses its policy trained with only if the files its reference names are on this box and carry those masses:
  - a grasp-lock masses retrain names refs/mass1_sf/ep<N>/assets (its own copy, tools/mass_arm.py): the pack must pull
    it (RUNS entry RUN@refs/mass1_sf/ep<N>,refs/mass1s<seed>_glockt/ep<N>);
  - a standard-learner retrain names the ONE shared /content/assets: the pack must build it with the same MA_ARGS
    (--physics PROPS) and pieces, and then no other episode whose reference names /content/assets may be evaluated.
For every episode about to be evaluated (CHECKPOINTS, e.g. pack_eval's checkpoints_eval.json) this follows that chain
and requires: every URDF resolves verbatim (a file); episodes in --mass-eps load the props' mass_kg for every object,
every other evaluated episode loads the 0.3 kg placeholder; for --mass-eps episodes with a --table row, the reference's
fingerprint (tools/mass_arm.traj_fingerprint) is the packed policy's (PLAN section 1) and, where the table names
collision pieces (eval 1 ev01, eval 10 ev10, eval 25 ev25), each such object's URDF has one <collision> per piece (as it
trained; e.g. a pack without ASSET_PIECES_EXTRA ev01 would evaluate eval 1 on the plain pot). A --mass-eps episode not being
evaluated here (kept rollout, KEEP_RESULTS) is listed as kept; one that is not in --all at all is a failure (typo).
Saved paths under /workspace/ are read under --content (the box links /content -> /workspace). No ground truth is read.
Exit 1 on any failure. Usage:
  mass_pack_check.py --checkpoints CK_EVAL.json [--all CK_ALL.json] --props PROPS.json --mass-eps "1 20 33"
                     [--table packed_refs.json] [--content /content] --out OUT.json
"""
import argparse, glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from mass_arm import read_inertial, traj_fingerprint, md5, PLACEHOLDER   # noqa: E402
from mass_verify import ck_config, resolve_parquet                         # noqa: E402
import pyarrow.parquet as pq                                               # noqa: E402


def localize(p, content):
    """A path saved on a box (/workspace/... = /content/...) read under this box's content root."""
    for r in ('/workspace/', '/content/'):
        if p.startswith(r) and content.rstrip('/') + '/' != r:
            return content.rstrip('/') + '/' + p[len(r):]
    return p


def chain(ck, content):
    """What the kit evaluator loads for one checkpoint: (reference file, its fingerprint and md5, {object: (urdf, mass,
    how)}) with how = 'verbatim' or 'NOT A FILE'."""
    _, cfg = ck_config(ck)
    rp = resolve_parquet(os.path.realpath(localize(cfg['task']['parquet'], content)))
    t = pq.read_table(rp); loaded = {}
    for n, u in zip(t.column('object_body_names')[0].as_py(), t.column('object_urdf_paths')[0].as_py()):
        lu = localize(u, content)
        if os.path.isfile(lu):
            loaded[n] = dict(urdf=lu, mass=read_inertial(open(lu).read())[0], how='verbatim', md5=md5(lu))
        else:
            loaded[n] = dict(urdf=lu, mass=None, how='NOT A FILE: FlashCHORD would re-root it on its own assets')
    return rp, traj_fingerprint(t), md5(rp), loaded


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--checkpoints', required=True); ap.add_argument('--all', default='')
    ap.add_argument('--props', required=True); ap.add_argument('--mass-eps', default='')
    ap.add_argument('--table', default=''); ap.add_argument('--content', default='/content'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ev = json.load(open(a.checkpoints)); allc = json.load(open(a.all)) if a.all else ev
    props = {n: float(v['physics']['mass_kg']) for n, v in json.load(open(a.props)).items() if isinstance(v, dict) and 'physics' in v}
    tab = json.load(open(a.table))['episodes'] if a.table else {}
    mass = {str(int(x)) for x in a.mass_eps.split()}; fails, rows = [], {}
    for e in sorted(mass - set(allc), key=int):
        fails.append(f'ep{e}: in MASS_EPS but not in the pack\'s checkpoints')
    for e in sorted(ev, key=int):
        row = rows[e] = dict(checkpoint=ev[e], mass_trained=e in mass)
        try:
            rp, fp, m5, loaded = chain(ev[e], a.content)
        except Exception as x:
            row['error'] = f'{type(x).__name__}: {str(x)[:200]}'; fails.append(f'ep{e}: {row["error"]}'); continue
        row.update(reference=rp, traj_fingerprint=fp, reference_md5=m5, loaded=loaded)
        for n, v in loaded.items():
            if v['mass'] is None:
                fails.append(f'ep{e}: {n}: {v["urdf"]} {v["how"]}'); continue
            want = props.get(n) if e in mass else PLACEHOLDER
            if want is None or abs(v['mass'] - want) > 1e-9:
                fails.append(f'ep{e}: {n} would be evaluated with {v["mass"]} kg ({v["urdf"]}); its policy trained with '
                             f'{want if want is not None else "?"} kg ({"masses retrain" if e in mass else "placeholder"})')
        if e in mass and e in tab and fp != tab[e]['traj_fingerprint']:
            fails.append(f'ep{e}: reference fingerprint {fp} is not the packed policy\'s {tab[e]["traj_fingerprint"]}')
        if e in mass and e in tab and tab[e].get('pieces'):                  # the collision pieces it trained with
            for n, v in loaded.items():
                k = len(glob.glob(os.path.join(REPO, tab[e]['pieces'], n, 'piece_*.obj')))
                c = len(re.findall(r'<collision>', open(v['urdf']).read())) if v['mass'] is not None else None
                v['collisions'] = c
                if k and c != k:
                    fails.append(f'ep{e}: {n} has {c} collision pieces ({v["urdf"]}), it trained with the {k} of {tab[e]["pieces"]}')
    kept = sorted(mass & set(allc) - set(ev), key=int)
    shared = {e: sorted({os.path.dirname(os.path.dirname(v['urdf'])) for v in r.get('loaded', {}).values()}) for e, r in rows.items()}
    out = dict(ok=not fails, failures=fails, mass_eps=sorted(mass, key=int), evaluated=sorted(ev, key=int), kept_mass_eps=kept,
               asset_roots=shared, episodes=rows)
    json.dump(out, open(a.out, 'w'), indent=1)
    print(('mass_pack_check: OK' if not fails else f'mass_pack_check: REFUSED ({len(fails)}): ' + ' | '.join(fails[:6]))
          + f' :: evaluated {sorted(ev, key=int)}, masses {sorted(mass & set(ev), key=int)}, kept {kept} :: '
          + '; '.join(f'ep{e} ' + ','.join(f'{n} {v["mass"]}' for n, v in r.get('loaded', {}).items()) for e, r in rows.items()))
    sys.exit(0 if not fails else 1)


if __name__ == '__main__':
    main()
