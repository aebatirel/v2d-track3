"""sim_vs_ref, plain and symmetric, plus per-frame error timelines (2026-11-01, perfect-following lane; no ground truth).

Reads an official evaluator rollout (RES/episode_XXXXXX.parquet: simulated object poses + the reference they track) and
scores the simulated poses against OUR reference exactly as pipeline/qa.py does (plain ADD on a 5 cm sphere, the kit's
_warp_to_reference_start, the kit's _add_auc), and a second time with the leaderboard's symmetry rule for cups: any spin
about the body z axis is free (the kit's _symmetry_point_errors, order 360). Cups' body z is their symmetry axis in our
library and in the public scans (vertex PCA, 1 Nov: |z . axis| >= 0.88 beige, 1.00 blue). The lid's 180-degree flip is
not applied (lids never flip in our rollouts).

Per frame and object it also returns the plain ADD, the symmetric ADD and the position error (cm), and per object the
onset frame: the first frame from which the symmetric ADD stays > ONSET_CM for ONSET_RUN frames.

  python tools/simref_timeline.py RES_DIR EP [--kit KIT] [--json OUT]
Library use: timeline(res_dir, ep, kit) -> dict
"""
import argparse, importlib, json, os, sys
import numpy as np

SYM_Z = {'blue_cup', 'beige_cup'}
ONSET_CM, ONSET_RUN = 3.0, 8


def _kit(kit):
    for p in (kit, f'{kit}/metric_code/track_3'):
        if p not in sys.path: sys.path.insert(0, p)
    return importlib.import_module('AUC')


def timeline(res, ep, kit, names=None):
    A = _kit(kit)
    import pandas as pd
    df = pd.read_parquet(os.path.join(res, f'episode_{ep:06d}.parquet'))
    from v2dlb.submission_parquet import read_trajectory
    tr = read_trajectory(os.path.join(res, f'episode_{ep:06d}.parquet'))
    w0 = tr.world_index == tr.world_index.min()
    frames = np.unique(tr.frame_index[w0]); B = int(tr.object_slot.max()) + 1
    names = list(names) if names else [None] * B
    if names == [None] * B and 'object_name' in df.columns:
        for s, n in df[['object_slot', 'object_name']].drop_duplicates().itertuples(index=False):
            names[int(s)] = str(n)

    def grid(P):
        G = np.full((len(frames), B, 7), np.nan)
        for f, s, p in zip(tr.frame_index[w0], tr.object_slot[w0], P[w0]):
            G[np.searchsorted(frames, f), s] = p
        return G
    sim, ref = grid(tr.pose_xyzw), grid(tr.reference_xyzw)
    rng = np.random.default_rng(0); pts = rng.normal(size=(500, 3)); pts = 0.05 * pts / np.linalg.norm(pts, axis=1, keepdims=True)
    V = np.repeat(pts[None], B, 0)
    a, r = sim[:, None], ref[:, None]
    a = A._warp_to_reference_start(a, r)
    plain = A._object_add(a, r, V)                                  # (T, 1, B) metres
    sym = plain.copy()
    for s in range(B):
        if names[s] in SYM_Z:
            sym[:, :, s] = A._symmetry_point_errors(a[:, :, s], r[:, :, s], pts, np.array([0., 0., 1.]), 360)
    pos = np.linalg.norm(a[..., :3] - r[..., :3], axis=-1)
    out = dict(ep=ep, frames=len(frames), names=names,
               sim_vs_ref=round(float(A._add_auc(plain)), 4), sim_vs_ref_sym=round(float(A._add_auc(sym)), 4),
               per_body=[round(float(A._add_auc(plain[..., s:s + 1])), 4) for s in range(B)],
               per_body_sym=[round(float(A._add_auc(sym[..., s:s + 1])), 4) for s in range(B)],
               add_cm=np.round(plain[:, 0] * 100, 2).tolist(), adds_cm=np.round(sym[:, 0] * 100, 2).tolist(),
               pos_cm=np.round(pos[:, 0] * 100, 2).tolist(), onset=[])
    for s in range(B):
        e = sym[:, 0, s] * 100 > ONSET_CM; on = None
        for t in range(len(e) - ONSET_RUN + 1):
            if e[t:t + ONSET_RUN].all(): on = int(frames[t]); break
        out['onset'].append(on)
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('res'); p.add_argument('ep', type=int)
    p.add_argument('--kit', default=os.environ.get('KIT', '/content/kit/v2d_submission_kit'))
    p.add_argument('--json', default=None)
    p.add_argument('--names', default=None, help='comma-separated object names in slot order (default: parquet column)')
    a = p.parse_args()
    o = timeline(a.res, a.ep, a.kit, a.names.split(',') if a.names else None)
    if a.json: json.dump(o, open(a.json, 'w'))
    print(json.dumps({k: o[k] for k in ('ep', 'names', 'sim_vs_ref', 'sim_vs_ref_sym', 'per_body', 'per_body_sym', 'onset')}))
