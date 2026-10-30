"""Pixal3D multi-view (TencentARC/Pixal3D main, MIT; TRELLIS.2 backbone) on OUR posed views, shape only.

Batch-2 generative probe, 2026-10-29. Runs on the box in env A (box_setup.sh). Inputs per object: a view directory
made by mv_views.py from our colour frames, our tracked poses and our calibration only (no scan, no mocap):
    transforms.json   Pixal3D/NeRF convention (c2w, Z-up world, camera looks -Z, per-frame camera_angle_x);
                      view 0 is placed exactly at the canonical front pose F, so the generation frame IS this world
    view*.png         1024x1024 RGBA, virtual recentred pinhole crops (principal point at the centre), alpha = mask
    probe_meta.json   s, c, A with p_world = s * A @ (p_obj - c)  (p_obj: our object frame, metres)
Outputs per (view dir, seed) in --out:
    <tag>_s<seed>_gen.ply   raw generator coordinates g in [-0.5, 0.5]^3
    <tag>_s<seed>.ply       the same mesh in our object frame: p_obj = c + A^T (R_GRID g) / s
    gen_log.jsonl           timing, face counts, resolution
R_GRID is Pixal3D's ProjGrid convention (image_conditioned_proj.py: grid points are rotated by R_GRID before they
are projected), i.e. voxel coordinates g map to world points R_GRID g / mesh_scale (mesh_scale = 1 here).
Gated repos named by the released config are swapped for public mirrors (DINOv3: camenduru mirror, which the
released inference_mv.py itself uses; RMBG-2.0 -> ZhengPeng7/BiRefNet; matting is unused since every view has alpha).
Usage: gen_pixal_mv.py --out DIR [--seeds 42,7] [--res 1536] [--num_views N] [--suffix X] VIEWDIR ...
"""
import argparse, json, os, sys, time

os.environ.setdefault('ATTN_BACKEND', 'flash_attn_3')
CODE = os.environ.get('PIXAL3D_CODE', '/content/ext/Pixal3D')
W = os.environ.get('PIXAL3D_W', '/content/w/Pixal3D')
sys.path.insert(0, CODE)
ORIG_CWD = os.getcwd()                             # view dirs on the command line are relative to this
os.chdir(CODE)                                     # inference_mv keeps its flex_gemm autotune cache next to itself
import numpy as np                                 # noqa: E402
import torch                                       # noqa: E402
import trimesh                                     # noqa: E402
import inference_mv as im                          # noqa: E402  (Pixal3D's own loaders)

R_GRID = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])


def patched_config():
    cfg = json.load(open(f'{W}/pipeline_mv.json'))
    a = cfg['args']
    a['rembg_model']['args']['model_name'] = 'ZhengPeng7/BiRefNet'
    a['image_cond_model']['args']['model_name'] = 'camenduru/dinov3-vitl16-pretrain-lvd1689m'
    for k in ('tex_slat_decoder', 'tex_slat_flow_model_1024'):
        a['models'].pop(k, None)
    json.dump(cfg, open(f'{W}/pipeline_mv_shape.json', 'w'), indent=1)
    return 'pipeline_mv_shape.json'


def shape_only(p):
    """Skip the texture stage: geometry comes from the shape latent alone."""
    p.models['tex_slat_flow_model_1024'] = torch.nn.Identity()       # run() only asserts that it exists
    orig = p.get_proj_cond_shape

    def cond(image_cond_model, *a, **k):
        if image_cond_model is p.image_cond_model_tex_1024:
            return None
        return orig(image_cond_model, *a, **k)

    def decode(shape_slat, tex_slat, res):
        meshes, _ = p.decode_shape_slat(shape_slat, res)
        for m in meshes:
            m.fill_holes()
        return meshes

    p.get_proj_cond_shape = cond
    p.sample_tex_slat = lambda *a, **k: None
    p.decode_latent = decode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True); ap.add_argument('--seeds', default='42,7')
    ap.add_argument('--res', type=int, default=1536); ap.add_argument('--num_views', type=int, default=None)
    ap.add_argument('--max_faces', type=int, default=400000); ap.add_argument('--suffix', default='')
    ap.add_argument('views', nargs='+')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    p = im.init_pipeline(W, patched_config(), low_vram=False)
    shape_only(p)
    print(f'[probe] pipeline ready in {time.time() - t0:.0f} s', flush=True)
    log = open(os.path.join(a.out, 'gen_log.jsonl'), 'a')
    for vd in a.views:
        vd = os.path.join(ORIG_CWD, vd)
        tag = os.path.basename(vd.rstrip('/')) + a.suffix
        views = im.load_views(vd, a.num_views, rembg=None)
        im.check_main_view(views)
        meta = json.load(open(os.path.join(vd, 'probe_meta.json')))
        s, c, A = float(meta['s']), np.array(meta['c'], float), np.array(meta['A'], float)
        for seed in [int(x) for x in a.seeds.split(',')]:
            t1 = time.time()
            rec = dict(model='pixal3d_mv', tag=tag, seed=seed, views=len(views['view_names']), res=a.res)
            try:
                torch.manual_seed(seed)
                meshes, (_, _, res) = p.run_mv(views, seed=seed, return_latent=True,
                                               pipeline_type=f'{a.res}_cascade', max_num_tokens=49152)
                m = meshes[0]
                rec['faces_raw'] = int(m.faces.shape[0]); rec['res_used'] = int(res)
                if m.faces.shape[0] > a.max_faces:
                    m.simplify(a.max_faces)
                g = m.vertices.detach().float().cpu().numpy().astype(np.float64)
                f = m.faces.detach().cpu().numpy().astype(np.int64)
                base = os.path.join(a.out, f'{tag}_s{seed}')
                trimesh.Trimesh(g, f, process=False).export(base + '_gen.ply')
                pw = g @ R_GRID.T
                po = c + (pw / s) @ A                     # A^T applied to row vectors
                trimesh.Trimesh(po, f, process=False).export(base + '.ply')
                rec.update(ok=True, faces=int(len(f)), g_min=g.min(0).round(4).tolist(), g_max=g.max(0).round(4).tolist(),
                           obj_extent_m=(po.max(0) - po.min(0)).round(4).tolist(), path=base + '.ply')
            except Exception as e:                           # keep going; the failure is recorded
                rec.update(ok=False, error=repr(e)[:500])
            rec['sec'] = round(time.time() - t1, 1)
            print(json.dumps(rec), flush=True); log.write(json.dumps(rec) + '\n'); log.flush()
            torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
