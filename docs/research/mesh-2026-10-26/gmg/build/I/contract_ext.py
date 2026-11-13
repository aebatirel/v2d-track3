"""INTERLOCK contract test, Embodiment side (round-1 fix B1; NOT a gmg process: it writes a parquet and runs the
Embodiment session's own tools, unmodified, from their branch). GT-free: reads our tracks (data/sweep/ep<N>/poses.npz),
our bundle's episode.json (table plane, object order) and our hands; never a dataset parquet, scan or mocap.

  python contract_ext.py --tracks .../data/sweep/ep24/poses.npz --episode-json .../bundle/public/ep24/episode.json
      --hands .../in/hands24/hands.npz --sim .../sim/public/ep24-r1evalsem/r0 --tool <dir with their tools/,
      pipeline/, ops/ from origin/claude/determined-wright-3joens> --emb-commit <their sha> --out OUTDIR [--max-nfev 3]

Steps (each command, return code, seconds and output tail go to OUTDIR/contract_ext.json):
  1. a REFERENCE parquet in mkref's layout (one row: object_body_names, object_body_position (T,B,3),
     object_body_wxyz (T,B,4) w-first, fps 20) from OUR tracks, in a table frame built from the bundle's frame-0 table
     plane (z = plane normal, objects above), plus REF.parquet.prov.json (pipeline/provenance.py manifest fields: tool,
     code_commit, run_id, sha256, command, inputs [{path, sha256}]) naming the tracks file as the perception input.
     This stands in for their perceived ep24 reference (not in this container; no HF token here).
  2. their tools/intrusion.py REF SIM OUT/e0.npz --round 0
  3. their pipeline/phys_fit.py IN OUT/fit --meshes SIM/_fit --props SIM/props_gmg.json --max_nfev N, with IN =
     poses.npz (our tracks), poses_world_vo.npz, table_frame.npz (the same table frame, no z shifts), hands.npz (ours).
     N = 3 is a PLUMBING run (does the fit read our props and _fit meshes and write its outputs), not a fit result.
  4. their tools/intrusion.py REF SIM OUT/e0fit.npz --round 0 --fit OUT/fit --fit_commit <their sha>
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def wxyz(R):
    from scipy.spatial.transform import Rotation as Rot
    q = Rot.from_matrix(R.reshape(-1, 3, 3)).as_quat()            # x, y, z, w
    q = q[:, [3, 0, 1, 2]]
    q[q[:, 0] < 0] *= -1
    return q.reshape(R.shape[:-2] + (4,))


def run(cmd, log, cwd=None):
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    rec = dict(cmd=cmd, rc=p.returncode, sec=round(time.time() - t, 1), stdout=p.stdout[-3000:], stderr=p.stderr[-3000:])
    log.append(rec)
    print(json.dumps({k: v for k, v in rec.items() if k in ('rc', 'sec')}), ' '.join(cmd)[:200], flush=True)
    if p.returncode:
        print(p.stdout[-2000:], p.stderr[-2000:], flush=True)
    return p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tracks', required=True); ap.add_argument('--episode-json', required=True)
    ap.add_argument('--hands', required=True); ap.add_argument('--sim', required=True)
    ap.add_argument('--tool', required=True); ap.add_argument('--emb-commit', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--max-nfev', type=int, default=3)
    ap.add_argument('--gmg-commit', default='')
    a = ap.parse_args()
    import pyarrow as pa
    import pyarrow.parquet as pq
    os.makedirs(a.out, exist_ok=True)
    log = []
    meta = json.load(open(a.episode_json))
    names = list(meta['objects'])
    ep = int(meta['ep'])
    P = np.load(a.tracks)
    T = len(P['world_T_cam'])
    W = np.stack([np.einsum('fij,fjk->fik', P['world_T_cam'].astype(np.float64), P[f'cam_T_{n}'].astype(np.float64))
                  for n in names], 1)                                                     # (T, B, 4, 4)
    # table frame from the bundle's frame-0 plane (camera 0 = world): z = normal pointing to the objects
    n = np.asarray(meta['table']['n'], float); d = float(meta['table']['d'])
    c0 = W[0, :, :3, 3].mean(0)
    if n @ c0 + d < 0:
        n, d = -n, -d
    o = c0 - (n @ c0 + d) * n
    x = np.cross([0, 1.0, 0], n); x /= np.linalg.norm(x); y = np.cross(n, x)
    Rt = np.stack([x, y, n])
    T_tab = np.eye(4); T_tab[:3, :3] = Rt; T_tab[:3, 3] = -Rt @ o
    O = np.einsum('ij,fbjk->fbik', T_tab, W)
    run_id = f'20261031-gmgref{ep}-{(a.gmg_commit or "0000000")[:7]}'
    rdir = os.path.join(a.out, 'runs', run_id, 'refs', f'ep{ep}', 'processed', f'sequence_id=t3_ep{ep:03d}',
                        'robot_name=none')
    os.makedirs(rdir, exist_ok=True)
    ref = os.path.join(rdir, 'ref.parquet')
    if not os.path.exists(ref):
        tab = pa.table({'object_body_names': [names], 'object_body_position': [O[:, :, :3, 3].tolist()],
                        'object_body_wxyz': [wxyz(O[:, :, :3, :3]).tolist()], 'fps': [20.0],
                        'sequence_id': [f't3_ep{ep:03d}']})
        pq.write_table(tab, ref)
        json.dump(dict(tool='docs/research/mesh-2026-10-26/gmg/build/I/contract_ext.py (gmg contract-test reference '
                            'writer: our tracks in a table frame, no snaps)', code_commit=a.gmg_commit, run_id=run_id,
                       sha256=sha(ref), command=' '.join(sys.argv),
                       inputs=[dict(path=os.path.abspath(a.tracks), sha256=sha(a.tracks)),
                               dict(path=os.path.abspath(a.episode_json), sha256=sha(a.episode_json))]),
                  open(ref + '.prov.json', 'w'), indent=1)
    py = sys.executable
    tool = os.path.join(a.tool, 'tools', 'intrusion.py')
    e0 = os.path.join(a.out, 'e0.npz')
    if not os.path.exists(e0):
        run([py, tool, ref, a.sim, e0, '--round', '0'], log)
    # phys_fit input folder
    fin = os.path.join(a.out, 'fitin')
    os.makedirs(fin, exist_ok=True)
    np.savez(os.path.join(fin, 'poses.npz'), **{k: P[k] for k in P.files})
    np.savez(os.path.join(fin, 'poses_world_vo.npz'), **{nm: W[:, b] for b, nm in enumerate(names)})
    np.savez(os.path.join(fin, 'table_frame.npz'), T_table_from_world=T_tab, plane_n=n, plane_d=d,
             names=np.array(names), object_z_shift=np.zeros(len(names)), table_z=0.0,
             table_disc=np.array([0.0, 0.0, 0.5]))
    H = np.load(a.hands)
    np.savez(os.path.join(fin, 'hands.npz'), **{k: H[k] for k in ('joints_left', 'joints_right', 'valid_left',
                                                                  'valid_right')})
    fout = os.path.join(a.out, 'fit')
    if not os.path.exists(os.path.join(fout, 'phys_fit.json')):
        run([py, os.path.join(a.tool, 'pipeline', 'phys_fit.py'), fin, fout, '--meshes', os.path.join(a.sim, '_fit'),
             '--props', os.path.join(a.sim, 'props_gmg.json'), '--max_nfev', str(a.max_nfev)], log)
    e1 = os.path.join(a.out, 'e0fit.npz')
    if not os.path.exists(e1) and os.path.exists(os.path.join(fout, 'phys_fit.json')):
        run([py, tool, ref, a.sim, e1, '--round', '0', '--fit', fout, '--fit_commit', a.emb_commit], log)
    rep = dict(reference=ref, reference_sha256=sha(ref), T_table_from_world=T_tab.tolist(), names=names, T=T,
               exports=[e0, e1], steps=log, note='reference built from OUR tracks (stand-in for their perceived ep24 '
                                                 'reference); phys_fit max_nfev = plumbing only')
    json.dump(rep, open(os.path.join(a.out, 'contract_ext.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
