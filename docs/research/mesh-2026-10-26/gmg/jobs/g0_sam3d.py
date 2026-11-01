"""G0 box runner (build step B3; PREREG B.12; SPEC section 18): SAM 3D Objects with OUR metric depth as the pointmap.

Runs on the GPU box in env C (gmg/jobs/g0_setup.sh: py3.10, torch 2.6 cu124, sam-3d-objects at f91db41). For every
job of INPUTS/jobs.json (written by gmg/tools/g0_inputs.py on the CPU) and every seed:
  rgba   = the undistorted cam_a frame with the target mask as alpha (<tag>.png, <tag>_mask.png);
  points = our FoundationStereo depth of that frame as an OpenCV-camera pointmap (<tag>_pointmap.npz, metres, NaN
           outside the mask), rotated into the PyTorch3D camera convention exactly as the organiser wrapper does
           (v2d_sam3d image_to_mesh._depth_to_pointmap: Transform3d().rotate(camera_to_pytorch3d_camera().rotation));
  out    = pipeline.run(rgba, None, seed, stage1_only=False, with_mesh_postprocess=False, with_texture_baking=False,
           with_layout_postprocess=False, use_vertex_color=True, pointmap=points, decode_formats=['mesh']):
           raw mesh-decoder output (no GLB post-processing), layout (rotation, translation, scale) de-normalised with
           the pointmap's scale/shift (so metric).
The mesh is moved into the camera with the library's own compose_transform (scale, rotate, translate; PyTorch3D row
vectors) and the inverse camera-convention rotation; the 4x4 camA_T_mesh (column vectors, OpenCV camera) is solved
from those transformed points and checked on every vertex. A GT-free convention check: distance from the input pointmap
points to the posed mesh's vertices (median, p90) and the organiser's closed form (R_net = Nxy R_q^T F^T for GLB
vertices, i.e. Nxy R_q^T for raw ones) against the library path.

Outputs in OUT/: <tag>_s<seed>.ply (raw mesh, local frame, decimated to <= MAX_FACES only if larger), <tag>_s<seed>.json
(layout, camA_T_mesh, obj_T_mesh = inv(camA_T_obj) camA_T_mesh, checks, runtime, sha256 of inputs and output),
gen_log.jsonl. Nothing is scored here.
Usage: g0_sam3d.py --ckpt DIR/pipeline.yaml --inputs DIR --out DIR [--max_faces 400000]
"""
import argparse
import hashlib
import json
import os
import sys
import time

CODE = os.environ.get('SAM3D_CODE', '/content/ext/sam-3d-objects')
os.environ.setdefault('LIDRA_SKIP_INIT', '1')         # the package's init hook is not in the public repo
sys.path.insert(0, CODE)
import numpy as np                                 # noqa: E402
import torch                                       # noqa: E402
import trimesh                                     # noqa: E402
from PIL import Image                              # noqa: E402


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def affine_from(points_in, points_out):
    """Least-squares 4x4 (column vectors) with out = A in + b."""
    X = np.hstack([points_in, np.ones((len(points_in), 1))])
    M, *_ = np.linalg.lstsq(X, points_out, rcond=None)
    T = np.eye(4)
    T[:3, :4] = M.T
    return T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--inputs', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--max_faces', type=int, default=400000)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    from omegaconf import OmegaConf
    from hydra.utils import instantiate
    import sam3d_objects  # noqa: F401
    from pytorch3d.transforms import Transform3d, quaternion_to_matrix
    from sam3d_objects.data.dataset.tdfy.transforms_3d import compose_transform
    from sam3d_objects.pipeline.inference_pipeline_pointmap import camera_to_pytorch3d_camera
    t0 = time.time()
    cfg = OmegaConf.load(a.ckpt)
    cfg.rendering_engine = 'pytorch3d'
    cfg.compile_model = False
    cfg.workspace_dir = os.path.dirname(a.ckpt)
    pipe = instantiate(cfg)

    def no_post(outputs, *args, **kw):                 # raw decoder mesh only (no GLB / texture post-processing)
        outputs['glb'] = None
        return outputs
    pipe.postprocess_slat_output = no_post
    dev = 'cuda'
    Rc = camera_to_pytorch3d_camera(device=dev).rotation          # OpenCV camera -> PyTorch3D camera (row vectors)
    to_p3d = Transform3d(device=dev).rotate(Rc)
    print(f'[g0] SAM 3D ready in {time.time() - t0:.0f} s on {torch.cuda.get_device_name(0)}', flush=True)
    jobs = json.load(open(os.path.join(a.inputs, 'jobs.json')))
    lp = os.path.join(a.out, 'gen_log.jsonl')
    done = set()
    if os.path.exists(lp):
        for line in open(lp):
            r = json.loads(line)
            if r.get('ok'):
                done.add((r['tag'], r['seed']))
    log = open(lp, 'a')
    for job in jobs:
        tag = job['tag']
        meta = json.load(open(os.path.join(a.inputs, f'{tag}.json')))
        files = {k: os.path.join(a.inputs, v) for k, v in meta['files'].items()}
        sha_in = {k: sha256(p) for k, p in files.items()}
        bad = [k for k in sha_in if sha_in[k] != meta['sha256'][k]]
        rgb = np.array(Image.open(files['rgb']).convert('RGB'))
        mask = np.array(Image.open(files['mask'])) > 127
        P = np.load(files['pointmap'])['points'].astype(np.float32)
        camA_T_obj = np.array(meta['camA_T_obj'], np.float64)
        for seed in job['seeds']:
            if (tag, int(seed)) in done:
                continue
            rec = dict(model='sam3d', tag=tag, seed=int(seed), obj=meta['obj'], kind=meta['kind'], k=meta['k'],
                       j=meta['j'], sha256_inputs=sha_in, sha256_mismatch=bad, mask_px=int(mask.sum()),
                       pointmap_valid_px=int(np.isfinite(P).all(-1).sum()))
            t1 = time.time()
            try:
                if bad:
                    raise ValueError(f'input sha256 mismatch: {bad}')
                rgba = np.concatenate([rgb, (mask.astype(np.uint8) * 255)[..., None]], -1)
                pm = to_p3d.transform_points(torch.from_numpy(P).to(dev))
                torch.cuda.reset_peak_memory_stats()
                out = pipe.run(rgba, None, int(seed), stage1_only=False, with_mesh_postprocess=False,
                               with_texture_baking=False, with_layout_postprocess=False, use_vertex_color=True,
                               pointmap=pm, decode_formats=['mesh'])
                rec['gpu_peak_gb'] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
                m = out['mesh'][0]
                v = m.vertices.detach().float()
                f = m.faces.detach().cpu().numpy().astype(np.int64)
                q, tr, sc = out['rotation'], out['translation'], out['scale']
                T = compose_transform(scale=sc.float(), rotation=quaternion_to_matrix(q.float()), translation=tr.float())
                vp3d = T.transform_points(v[None])[0]
                vcv = to_p3d.inverse().transform_points(vp3d).detach().cpu().numpy().astype(np.float64)
                vl = v.cpu().numpy().astype(np.float64)
                A = affine_from(vl, vcv)
                fit = np.abs(vl @ A[:3, :3].T + A[:3, 3] - vcv).max()
                # organiser closed form (image_to_mesh._to_opencv_transform without the GLB axis change)
                from scipy.spatial.transform import Rotation
                w_, x_, y_, z_ = [float(x) for x in q[0].tolist()]
                Rq = Rotation.from_quat([x_, y_, z_, w_]).as_matrix()
                Nxy = np.diag([-1.0, -1.0, 1.0])
                s_ = np.asarray(sc[0].tolist(), np.float64)
                vcf = (vl * s_) @ (Nxy @ Rq.T).T + Nxy @ np.asarray(tr[0].tolist(), np.float64)
                rec['closed_form_max_m'] = float(np.abs(vcf - vcv).max())
                rec['affine_fit_max_m'] = float(fit)
                # GT-free layout check: input pointmap points -> nearest posed vertex
                from scipy.spatial import cKDTree
                Q = P[np.isfinite(P).all(-1)].astype(np.float64)
                if len(Q) > 20000:
                    Q = Q[np.random.default_rng(0).choice(len(Q), 20000, replace=False)]
                dq, _ = cKDTree(vcv).query(Q, k=1)
                rec['pointmap_to_mesh_mm'] = dict(median=round(float(np.median(dq)) * 1e3, 3),
                                                  p90=round(float(np.percentile(dq, 90)) * 1e3, 3),
                                                  n=int(len(Q)))
                obj_T_mesh = np.linalg.inv(camA_T_obj) @ A
                tm = trimesh.Trimesh(vl, f, process=False)
                rec['faces_raw'] = int(len(f))
                if len(f) > a.max_faces:
                    import fast_simplification
                    v2, f2 = fast_simplification.simplify(tm.vertices, tm.faces, 1 - a.max_faces / len(f))
                    tm = trimesh.Trimesh(v2, f2, process=False)
                    rec['decimated_to'] = int(len(tm.faces))
                path = os.path.join(a.out, f'{tag}_s{seed}.ply')
                tm.export(path)
                ext_cam = (vcv.max(0) - vcv.min(0))
                rec.update(ok=True, path=os.path.basename(path), sha256_mesh=sha256(path),
                           layout=dict(rotation_wxyz=[float(x) for x in q[0].tolist()],
                                       translation_p3d=[float(x) for x in tr[0].tolist()],
                                       scale=[float(x) for x in sc[0].tolist()]),
                           camA_T_mesh=A.tolist(), obj_T_mesh=obj_T_mesh.tolist(), camA_T_obj=camA_T_obj.tolist(),
                           extent_local=(vl.max(0) - vl.min(0)).round(4).tolist(),
                           extent_cam_m=ext_cam.round(4).tolist())
            except Exception as e:                       # noqa: BLE001
                import traceback
                traceback.print_exc()
                rec.update(ok=False, error=repr(e)[:800])
            rec['sec'] = round(time.time() - t1, 1)
            with open(os.path.join(a.out, f'{tag}_s{seed}.json'), 'w') as fj:
                json.dump(rec, fj, indent=1)
            print(json.dumps({k: rec.get(k) for k in ('tag', 'seed', 'ok', 'sec', 'faces_raw', 'pointmap_to_mesh_mm',
                                                       'closed_form_max_m', 'gpu_peak_gb', 'error')}), flush=True)
            log.write(json.dumps(rec) + '\n')
            log.flush()
            torch.cuda.empty_cache()
    print('[g0] G0-SAM3D-DONE', flush=True)


if __name__ == '__main__':
    main()
