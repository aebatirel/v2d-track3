"""Build the FINAL edited actor (v10) deterministically from the original exercise-3 actor.npz, and the pre-registered
random-edit control.

Usage:
  python -I edit.py ORIGINAL_ACTOR_NPZ OUT_EDIT_NPZ [OUT_RANDOM_NPZ [OUT_RANDOM_SANITIZED_NPZ]]

Final edit (v10, see build.py and README.md): four hand-built controllers in private residual-stream coordinates.
  1. Joint6_R virtual limit: offset q - ref <= training mean + 1.5 sd (+0.222 rad); coordinate 78, gate unit 887.
  2. Left-wrist orientation controller for the approach (error about body axis n = (0,1,1)/sqrt2 > 0.15 rad ->
     Joint5-7_L), switched off while the left hand grasps or holds; coordinate 39, units 777 (gate), 659 and 106
     (inhibitors).
  3. End-phase left-wrist position cap (error along m > 0.10 m readout -> pinv(position Jacobian) m on Joint1-7_L);
     coordinate 159, unit 322.
  4. Left-hand release (mean left finger command < training mean - 3 sd -> open left fingers); coordinate 161, unit 67.
Constants derived from the kinematic model and rollout traces are stored in lwrist_controller.json and
lwrist_pos_controller.json (derivations inside).

Random control (pre-registered): the same entries changed, the change of each entry replaced by |change| with a random
sign (numpy default_rng(0), one draw per changed entry in sorted-key order), which keeps the Frobenius norm of the
change per matrix.
"""
import hashlib, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net, edits, build


def final_edit(w0):
    return build.v10(w0)


def random_control(w0, w1, seed=0):
    rng = np.random.default_rng(seed)
    out = {}
    for k in sorted(w0):
        a, b = w0[k].astype(np.float64), w1[k].astype(np.float64)
        d = b - a
        m = d != 0
        s = rng.choice([-1.0, 1.0], size=int(m.sum()))
        r = a.copy(); r[m] = a[m] + s * np.abs(d[m])
        out[k] = r.astype(w0[k].dtype)
    return out


def random_control_sanitized(w0, w1, seed=0):
    """Sensitivity check, NOT the pre-registered control: as random_control (same draws), except that a batch-norm
    running variance that would become <= 0 takes the positive sign instead. Same entries, same |change| per entry,
    same Frobenius norm per matrix. Needed because the literal control has 6 negative variances, which make the
    network output NaN (so it fails every run trivially)."""
    wr = random_control(w0, w1, seed)
    for k in wr:
        if k.endswith('running_variance'):
            a = w0[k].astype(np.float64); d = np.abs(w1[k].astype(np.float64) - a)
            bad = wr[k] <= 0
            wr[k] = wr[k].copy(); wr[k][bad] = (a[bad] + d[bad]).astype(w0[k].dtype)
    return wr


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    w0 = net.load(src)
    w1 = final_edit(w0)
    assert all(w1[k].shape == w0[k].shape and w1[k].dtype == w0[k].dtype for k in w0)
    edits.save(w1, out)
    d = edits.diff(w0, w1)
    info = {'edit': out, 'sha256': sha(out), 'changed': sum(v['changed'] for v in d.values()),
            'zeroed': sum(v['zeroed'] for v in d.values()), 'per_array': d}
    if len(sys.argv) > 3:
        wr = random_control(w0, w1)
        edits.save(wr, sys.argv[3])
        dr = edits.diff(w0, wr)
        info['random'] = {'path': sys.argv[3], 'sha256': sha(sys.argv[3]),
                          'fro_match': all(abs(dr[k]['fro'] - d[k]['fro']) < 1e-4 * max(1, d[k]['fro']) for k in d),
                          'changed': sum(v['changed'] for v in dr.values()),
                          'negative_variances': int(sum((wr[k] < 0).sum() for k in wr if k.endswith('running_variance')))}
    if len(sys.argv) > 4:
        ws = random_control_sanitized(w0, w1)
        edits.save(ws, sys.argv[4])
        ds = edits.diff(w0, ws)
        info['random_sanitized'] = {'path': sys.argv[4], 'sha256': sha(sys.argv[4]),
                                    'fro_match': all(abs(ds[k]['fro'] - d[k]['fro']) < 1e-4 * max(1, d[k]['fro']) for k in d),
                                    'negative_variances': int(sum((ws[k] <= 0).sum() for k in ws if k.endswith('running_variance')))}
    print(json.dumps({k: v for k, v in info.items() if k != 'per_array'}, indent=1))
    print(json.dumps(info['per_array']))
