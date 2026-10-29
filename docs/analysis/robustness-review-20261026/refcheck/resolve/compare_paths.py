"""Provenance check for the canonical public references (refcheck/resolve, 26 Oct 2026; CPU, no ground truth read).

For pairs of stored files it reports how far apart the OBJECT paths are:
  ref:<dir>        a reference dir (refs/<variant>/epN): object_body_position / object_body_wxyz of its processed parquet
  pq:<file>        any FlashCHORD reference parquet (sf / glock / glockt stages)
  res:<file>       an evaluator rollout parquet: its reference_position / reference_quaternion columns (xyzw)
Output: max / median position difference (mm) and max rotation difference (deg) per object, after removing the best
constant translation (the evaluator places the reference in its sim world, which may add a fixed offset), plus the raw
constant offset. Usage: python -I compare_paths.py STORE_ROOT OUT.json  (pairs are listed below).
"""
import glob, json, os, sys
import numpy as np
import pyarrow.parquet as pq


def load_ref_parquet(f):
    t = pq.read_table(f, columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
    names = t.column('object_body_names')[0].as_py()
    pos = np.array(t.column('object_body_position')[0].as_py(), float)          # T, n, 3
    wxyz = np.array(t.column('object_body_wxyz')[0].as_py(), float)            # T, n, 4
    return {n: (pos[:, i], wxyz[:, i]) for i, n in enumerate(names)}


def load_res(f):
    t = pq.read_table(f).to_pandas()
    meta = {k.decode(): v.decode() for k, v in (pq.read_schema(f).metadata or {}).items() if k.startswith(b'flash_chord')}
    out = {}
    for n, g in t.groupby('object_body_name', observed=True):
        g = g.sort_values('reference_frame')
        p = g[['reference_position_x', 'reference_position_y', 'reference_position_z']].to_numpy(float)
        q = g[['reference_quaternion_w', 'reference_quaternion_x', 'reference_quaternion_y', 'reference_quaternion_z']].to_numpy(float)
        out[str(n)] = (p, q, g['reference_frame'].to_numpy())
    return out, meta


def resolve(root, spec):
    kind, path = spec.split(':', 1)
    if kind == 'ref':
        fs = sorted(glob.glob(f'{root}/{path}/processed/*/*/*.parquet'))
        assert fs, spec
        return load_ref_parquet(fs[0]), {'file': fs[0][len(root) + 1:]}
    if kind == 'pq':
        return load_ref_parquet(f'{root}/{path}'), {'file': path}
    if kind == 'res':
        d, meta = load_res(f'{root}/{path}')
        return {n: (p, q) for n, (p, q, fr) in d.items()}, {'file': path, 'reference_parquet': meta.get('flash_chord.reference_parquet'),
                                                          'frames': int(max(len(v[2]) for v in d.values()))}
    raise ValueError(spec)


def qdiff_deg(a, b):
    a = a / np.linalg.norm(a, axis=1, keepdims=True); b = b / np.linalg.norm(b, axis=1, keepdims=True)
    return np.degrees(2 * np.arccos(np.clip(np.abs((a * b).sum(1)), 0, 1)))


def compare(root, A, B):
    a, ia = resolve(root, A); b, ib = resolve(root, B)
    rows = {}
    for n in sorted(set(a) & set(b)):
        pa, qa = a[n]; pb, qb = b[n]; T = min(len(pa), len(pb))
        d = pb[:T] - pa[:T]; off = np.median(d, 0); r = np.linalg.norm(d - off, axis=1) * 1000
        rows[n] = dict(frames=[len(pa), len(pb)], const_offset_mm=np.round(off * 1000, 2).tolist(),
                       max_mm=round(float(r.max()), 3), median_mm=round(float(np.median(r)), 3),
                       raw_max_mm=round(float((np.linalg.norm(d, axis=1) * 1000).max()), 3),
                       rot_max_deg=round(float(qdiff_deg(qa[:T], qb[:T]).max()), 3),
                       frames_over_1mm=int((r > 1).sum()))
    return dict(A=A, B=B, A_info=ia, B_info=ib, objects=rows, only_A=sorted(set(a) - set(b)), only_B=sorted(set(b) - set(a)))


PAIRS = [
    # ep2: e3 mck reference vs its own grasp-lock chain and its rollouts
    ('ref:runs/20261024-e3-e49e83d/refs/perc2mck/ep2', 'pq:runs/20261024-e3-e49e83d/refs/sf/ep2/processed/sequence_id=t3_ep002/robot_name=sharpa_wave/ref_sf.parquet'),
    ('ref:runs/20261024-e3-e49e83d/refs/perc2mck/ep2', 'pq:runs/20261024-e3-e49e83d/refs/glockt/ep2/processed/sequence_id=t3_ep002/robot_name=sharpa_wave/ref_gl_ilc.parquet'),
    ('ref:runs/20261024-e3-e49e83d/refs/perc2mck/ep2', 'res:runs/20261024-e3-e49e83d/results/glock_public/ep2/best/r1/episode_000002.parquet'),
    # ep39: e3 mck vs ev3 (frozen recipe) chain and rollouts
    ('ref:runs/20261024-e3-e49e83d/refs/perc2mck/ep39', 'pq:runs/20261024-ev3-2c1e4dd/refs/glockt/ep39/processed/sequence_id=t3_ep039/robot_name=sharpa_wave/ref_gl_ilc.parquet'),
    ('ref:runs/20261024-e3-e49e83d/refs/perc2mck/ep39', 'res:runs/20261024-ev3-2c1e4dd/results/glock_public/ep39/best/r1/episode_000039.parquet'),
    # ep11: twin11v3x / twin11v3
    ('ref:runs/20261025-twin11v3x-0e8aebb/refs/perc2mck/ep11', 'res:runs/20261025-twin11v3x-0e8aebb/results/glock_public/ep11/best/r1/episode_000011.parquet'),
    ('ref:runs/20261025-twin11v3-0e8aebb/refs/perc2mck/ep11', 'res:runs/20261025-twin11v3-0e8aebb/results/glock_public/ep11/best/r1/episode_000011.parquet'),
    ('ref:runs/20261025-twin11v3-0e8aebb/refs/perc2mck/ep11', 'ref:runs/20261025-twin11v3x-0e8aebb/refs/perc2mck/ep11'),
    # ep12: mc (auto18) vs mckd (fdr43 / fdr42); ev2 frozen-recipe rollouts on mc; fdr43 hard_ab rollouts on mckd
    ('ref:runs/20261021-auto18-966eb96/refs/perc2mc/ep12', 'ref:runs/20261023-fdr43-715c9f7/refs/perc2mckd/ep12'),
    ('ref:runs/20261023-fdr43-715c9f7/refs/perc2mckd/ep12', 'ref:runs/20261023-fdr42-715c9f7/refs/perc2mckd/ep12'),
    ('ref:runs/20261023-fdr43-715c9f7/refs/perc2mckd/ep12', 'res:runs/20261023-fdr43-715c9f7/results/hard_ab/ep12/mckd-s43/r1/episode_000012.parquet'),
    ('ref:runs/20261021-auto18-966eb96/refs/perc2mc/ep12', 'res:runs/20261024-ev2-2c1e4dd/results/glock_public/ep12/best/r1/episode_000012.parquet'),
    # ep18: mc vs mckfi (rest settle); ev3 frozen-recipe rollouts on the mckfid copy
    ('ref:runs/20261021-auto18-966eb96/refs/perc2mc/ep18', 'ref:runs/20261022-r4kfi-a30ac72/refs/perc2mckfi/ep18'),
    ('ref:runs/20261022-r4kfi-a30ac72/refs/perc2mckfi/ep18', 'res:runs/20261024-ev3-2c1e4dd/results/glock_public/ep18/best/r1/episode_000018.parquet'),
    ('ref:runs/20261022-r4kfi-a30ac72/refs/perc2mckfi/ep18', 'res:runs/20261022-r4kfi-a30ac72/results/hard_ab/ep18/mckfi-s42/r1/episode_000018.parquet'),
    # ep21: twin21arc / base
    ('ref:runs/20261025-twin21arc-ee7ba8e/refs/perc2mck/ep21', 'res:runs/20261025-twin21arc-ee7ba8e/results/glock_public/ep21/best/r1/episode_000021.parquet'),
    ('ref:runs/20261025-twin21base-ee7ba8e/refs/perc2mck/ep21', 'ref:runs/20261025-twin21arc-ee7ba8e/refs/perc2mck/ep21'),
    # ep24: mcs (auto24) vs mcsks (r5ks); ev3 frozen-recipe on mcs; r5ks hard_ab on mcsks; w1 mck (library_v4 track)
    ('ref:runs/20261021-auto24-966eb96/refs/perc2mcs/ep24', 'ref:runs/20261022-r5ks-72ecb2f/refs/perc2mcsks/ep24'),
    ('ref:runs/20261022-r5ks-72ecb2f/refs/perc2mcsks/ep24', 'res:runs/20261022-r5ks-72ecb2f/results/hard_ab/ep24/mcsks-s42/r1/episode_000024.parquet'),
    ('ref:runs/20261021-auto24-966eb96/refs/perc2mcs/ep24', 'res:runs/20261024-ev3-2c1e4dd/results/glock_public/ep24/best/r1/episode_000024.parquet'),
    ('ref:runs/20261021-auto24-966eb96/refs/perc2mcs/ep24', 'ref:runs/20261024-w1-37cc551/refs/perc2mck/ep24'),
    # ep26: w1
    ('ref:runs/20261024-w1-37cc551/refs/perc2mck/ep26', 'res:runs/20261024-w1-37cc551/results/glock_public/ep26/best/r1/episode_000026.parquet'),
    # ep27: mc vs mcki; ev2 frozen recipe on mc; r3kie hard_ab on mcki
    ('ref:runs/20261021-auto18-966eb96/refs/perc2mc/ep27', 'ref:runs/20261022-r3kie-342d72c/refs/perc2mcki/ep27'),
    ('ref:runs/20261022-r3kie-342d72c/refs/perc2mcki/ep27', 'res:runs/20261022-r3kie-342d72c/results/hard_ab/ep27/mcki-s42/r1/episode_000027.parquet'),
    ('ref:runs/20261021-auto18-966eb96/refs/perc2mc/ep27', 'res:runs/20261024-ev2-2c1e4dd/results/glock_public/ep27/best/r1/episode_000027.parquet'),
    # ep31: ev30rp
    ('ref:runs/20261024-ev30rp-07eef1a/refs/perc2mck/ep31', 'res:runs/20261024-ev30rp-07eef1a/results/glock_public/ep31/best/r1/episode_000031.parquet'),
]

if __name__ == '__main__':
    root, out = sys.argv[1], sys.argv[2]
    res = []
    for A, B in PAIRS:
        try:
            res.append(compare(root, A, B))
        except Exception as e:  # report, do not hide
            res.append(dict(A=A, B=B, error=repr(e)[:300]))
        r = res[-1]
        print(A.split('runs/')[1][:60], '->', B.split('runs/')[1][:80])
        print('   ', r.get('error') or {n: (o['max_mm'], o['rot_max_deg'], o['const_offset_mm'], o['frames']) for n, o in r['objects'].items()},
              (r.get('B_info') or {}).get('reference_parquet', ''))
    json.dump(res, open(out, 'w'), indent=1)
