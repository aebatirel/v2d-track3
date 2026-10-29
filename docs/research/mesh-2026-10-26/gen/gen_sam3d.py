"""SAM 3D Objects (facebookresearch/sam-3d-objects, SAM License; gated weights) on our RGBA crops, shape only.

Batch-2 generative probe, 2026-10-29 (added when the owner's gated access was approved during the run). Runs on the
box in env C. Input = our crop with its mask as alpha (crops.py); the pointmap comes from SAM 3D's own MoGe on the crop
(no scan, no ground truth). Texture baking, mesh post-processing and layout post-optimisation are off; the raw mesh of
the SLat mesh decoder is exported. Output: <out>/<crop tag>_s<seed>.ply in SAM 3D's object frame (arbitrary pose and
scale for our purpose; CD-O is similarity-invariant) and gen_log.jsonl.
Usage: gen_sam3d.py --ckpt DIR/pipeline.yaml --out DIR [--seeds 42,7] crop.png ...
"""
import argparse, json, os, sys, time

CODE = os.environ.get('SAM3D_CODE', '/content/ext/sam-3d-objects')
os.environ.setdefault('LIDRA_SKIP_INIT', '1')         # the package's init hook is not in the public repo
sys.path.insert(0, CODE)
import numpy as np                                 # noqa: E402
import torch                                       # noqa: E402
import trimesh                                     # noqa: E402
from PIL import Image                              # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--seeds', default='42,7'); ap.add_argument('--max_faces', type=int, default=400000)
    ap.add_argument('crops', nargs='+')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    from omegaconf import OmegaConf
    from hydra.utils import instantiate
    import sam3d_objects  # noqa: F401
    t0 = time.time()
    cfg = OmegaConf.load(a.ckpt)
    cfg.rendering_engine = 'pytorch3d'
    cfg.compile_model = False
    cfg.workspace_dir = os.path.dirname(a.ckpt)
    pipe = instantiate(cfg)

    def no_post(outputs, *args, **kw):                 # skip GLB/texture post-processing: raw decoder mesh only
        outputs['glb'] = None
        return outputs
    pipe.postprocess_slat_output = no_post
    print(f'[probe] SAM 3D ready in {time.time() - t0:.0f} s', flush=True)
    done = set()                                       # (tag, seed) already generated: skipped (resume/queues)
    lp = os.path.join(a.out, 'gen_log.jsonl')
    if os.path.exists(lp):
        for l in open(lp):
            r = json.loads(l)
            if r.get('ok'):
                done.add((r['tag'], r['seed']))
    log = open(lp, 'a')
    for crop in a.crops:
        tag = os.path.splitext(os.path.basename(crop))[0]
        rgba = np.array(Image.open(crop).convert('RGBA'))
        img, mask = rgba[..., :3], rgba[..., 3] > 127
        for seed in [int(x) for x in a.seeds.split(',')]:
            if (tag, seed) in done:
                continue
            t1 = time.time()
            rec = dict(model='sam3d', tag=tag, seed=seed, crop=crop)
            try:
                rgba_in = np.concatenate([img, (mask.astype(np.uint8) * 255)[..., None]], -1)
                out = pipe.run(rgba_in, None, seed, stage1_only=False, with_mesh_postprocess=False,
                               with_texture_baking=False, with_layout_postprocess=False, use_vertex_color=True,
                               decode_formats=['mesh'])
                m = out['mesh'][0]
                v = m.vertices.detach().float().cpu().numpy().astype(np.float64)
                f = m.faces.detach().cpu().numpy().astype(np.int64)
                tm = trimesh.Trimesh(v, f, process=False)
                rec['faces_raw'] = int(len(f))
                if len(f) > a.max_faces:
                    import fast_simplification
                    v2, f2 = fast_simplification.simplify(tm.vertices, tm.faces, 1 - a.max_faces / len(f))
                    tm = trimesh.Trimesh(v2, f2, process=False)
                path = os.path.join(a.out, f'{tag}_s{seed}.ply')
                tm.export(path)
                rec.update(ok=True, faces=int(len(tm.faces)), extent=(tm.vertices.max(0) - tm.vertices.min(0)).round(4).tolist(),
                           scale=np.asarray(out.get('scale', torch.zeros(1)).detach().cpu()).round(4).tolist()
                           if hasattr(out.get('scale', None), 'detach') else None, path=path)
            except Exception as e:
                import traceback
                traceback.print_exc()
                rec.update(ok=False, error=repr(e)[:500])
            rec['sec'] = round(time.time() - t1, 1)
            print(json.dumps(rec), flush=True); log.write(json.dumps(rec) + '\n'); log.flush()
            torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
