"""GT-free bookkeeping check for rts (PREREG §4 INVALID (a), (c)); reads only refine outputs, never mocap.
(a) default behaviour unchanged: for every (arm, episode) and variant S2 (control) and DEF (default chain, no --steps),
    the arrays of poses.npz, poses_world_vo.npz and pose_opt_aux.npz written by the code WITH S13 are byte-identical
    (key, dtype, shape, bytes) to those written before S13 existed ($W/runs_pre); pose_opt.json is compared with the
    run-specific fields (time_utc, code, argv, params) removed and the output dir normalised, and params compared
    without the new s13_* keys.
(c) S13 changes positions only: rotation difference between the written S2 and S2,S13 world poses, per frame; on frames
    whose rotation bytes differ (the last frame: S2 writes it unchanged, the writer orthonormalises it once S13 moves it)
    also against the orthonormal projection of the control's rotation (PREREG Amendment 1).
Usage: python -I rts_bytecheck.py OUT_JSON
"""
import hashlib, json, os, sys

import numpy as np

S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
W = f'{S}/rts'
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
ARMS = ('Po', 'refineP')
VOLATILE = ('time_utc', 'code', 'argv', 'params')


def arrays_equal(f1, f2):
    A, B = np.load(f1), np.load(f2)
    if A.files != B.files:
        return False, f'keys {A.files} vs {B.files}'
    for k in A.files:
        a, b = A[k], B[k]
        if a.dtype != b.dtype or a.shape != b.shape or a.tobytes() != b.tobytes():
            return False, f'{k} differs'
    return True, ''


def sha(f):
    return hashlib.sha256(open(f, 'rb').read()).hexdigest()


def json_equal(f1, f2):
    a = json.loads(open(f1).read().replace(f'{W}/runs_pre/', f'{W}/runs/'))     # the output dir appears in the log
    b = json.load(open(f2))
    pa = {k: v for k, v in a['params'].items()}
    pb = {k: v for k, v in b['params'].items() if not k.startswith('s13_')}
    extra = sorted(k for k in b['params'] if k.startswith('s13_'))
    for k in VOLATILE:
        a.pop(k, None), b.pop(k, None)
    return a == b and pa == pb, extra


def rot_deg(A, B):
    """Chordal angle 2 asin(|R_A - R_B|_F / (2 sqrt 2)): well conditioned near 0. (arccos((tr(R_A^T R_B) - 1) / 2) is
    not: on float32-derived rotations it reads ~0.02-0.1 deg even for A == B, since tr(A^T A) != 3 to ~1e-7.)"""
    d = np.linalg.norm((A[:, :3, :3] - B[:, :3, :3]).reshape(len(A), -1), axis=1)
    return np.degrees(2 * np.arcsin(np.clip(d / (2 * np.sqrt(2)), 0, 1)))


def polar(R):
    """Orthonormal projection of (F,3,3) as refine's writer computes it (U diag(1, 1, det) Vt)."""
    out = np.zeros((len(R), 4, 4))
    for i, M in enumerate(R):
        U, _, Vt = np.linalg.svd(M)
        out[i, :3, :3] = U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt
    return out


def main():
    out = dict(default_unchanged={}, s13_rotation={}, summary={})
    n_ok = n_all = 0
    file_bytes_same = 0
    for arm in ARMS:
        for v in ('S2', 'DEF'):
            for e in EPS:
                pre, post = f'{W}/runs_pre/{arm}/{v}/ep{e}', f'{W}/runs/{arm}/{v}/ep{e}'
                r = {}
                for f in ('poses.npz', 'poses_world_vo.npz', 'pose_opt_aux.npz'):
                    ok, why = arrays_equal(f'{pre}/{f}', f'{post}/{f}')
                    r[f] = ok if ok else why
                    file_bytes_same += sha(f'{pre}/{f}') == sha(f'{post}/{f}')
                ok, extra = json_equal(f'{pre}/pose_opt.json', f'{post}/pose_opt.json')
                r['pose_opt.json'] = ok
                r['new_params'] = extra
                good = all(x is True for k, x in r.items() if k != 'new_params')
                n_ok += good
                n_all += 1
                out['default_unchanged'][f'{arm}/{v}/ep{e}'] = r
        for e in EPS:
            A = np.load(f'{W}/runs/{arm}/S2/ep{e}/poses_world_vo.npz')
            B = np.load(f'{W}/runs/{arm}/S13/ep{e}/poses_world_vo.npz')
            d = {n: float(rot_deg(A[n], B[n]).max()) for n in A.files}
            dp = {n: float(np.linalg.norm(A[n][:, :3, 3] - B[n][:, :3, 3], axis=1).max() * 100) for n in A.files}
            same = {n: int(sum(A[n][t, :3, :3].tobytes() == B[n][t, :3, :3].tobytes() for t in range(len(A[n]))))
                    for n in A.files}
            diff_frames = {n: [int(t) for t in range(len(A[n])) if A[n][t, :3, :3].tobytes() != B[n][t, :3, :3].tobytes()]
                           for n in A.files}
            dpol = {}                                            # amended (c): vs the orthonormal projection
            for n in A.files:
                fr = diff_frames[n]
                dpol[n] = max([float(rot_deg(polar(A[n][fr, :3, :3]), B[n][fr, :3, :3]).max())] if fr else [0.0])
            out['s13_rotation'][f'{arm}/ep{e}'] = dict(max_rot_deg=d, max_pos_cm=dp, rot_frames_byte_identical=same,
                                                      T=len(A[A.files[0]]), rot_frames_differing=diff_frames,
                                                      max_rot_deg_vs_polar_on_differing=dpol)
    rmax = max(max(x['max_rot_deg'].values()) for x in out['s13_rotation'].values())
    nf = sum(sum(x['rot_frames_byte_identical'].values()) for x in out['s13_rotation'].values())
    nt = sum(x['T'] * len(x['rot_frames_byte_identical']) for x in out['s13_rotation'].values())
    where = sorted({(k, n, tuple(f)) for k, x in out['s13_rotation'].items() for n, f in x['rot_frames_differing'].items() if f})
    out['summary'] = dict(default_runs_identical=f'{n_ok}/{n_all}', npz_files_byte_identical=f'{file_bytes_same}/{3 * n_all}',
                          s13_rotation_frames_byte_identical=f'{nf}/{nt}', s13_rotation_frames_differing=[list(w) for w in where],
                          s13_max_rotation_change_deg=rmax, invalid_a=n_ok != n_all, invalid_c_as_first_written=rmax > 1e-4)
    rpol = max(max(x['max_rot_deg_vs_polar_on_differing'].values()) for x in out['s13_rotation'].values())
    rsame = max(max(v for n, v in x['max_rot_deg'].items() if not x['rot_frames_differing'][n]) if any(
        not x['rot_frames_differing'][n] for n in x['max_rot_deg']) else 0.0 for x in out['s13_rotation'].values())
    out['summary'].update(max_rot_deg_objects_without_differing_frames=rsame,
                          max_rot_deg_vs_polar_on_differing_frames=rpol,
                          invalid_c_amendment1=bool(rpol > 1e-4))
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
    print(json.dumps(out['summary'], indent=1))


if __name__ == '__main__':
    main()
