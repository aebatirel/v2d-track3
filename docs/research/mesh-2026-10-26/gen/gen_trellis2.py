"""TRELLIS.2-4B single image (microsoft/TRELLIS.2, MIT), shape only, on our RGBA crops (crops.py).

Batch-2 generative probe, 2026-10-29. Runs on the box in env A (box_setup.sh). The released pipeline.json names
two gated repos (facebook/dinov3-vitl16-pretrain-lvd1689m, briaai/RMBG-2.0); they are swapped for the public mirrors
camenduru/dinov3-vitl16-pretrain-lvd1689m and ZhengPeng7/BiRefNet (matting is unused: every crop has alpha). The
texture models are not loaded. Output: <out>/<crop tag>_s<seed>.ply in TRELLIS.2's canonical frame (arbitrary pose
and scale; CD-O is similarity-invariant) and gen_log.jsonl.
Usage: gen_trellis2.py --out DIR [--seeds 42,7] [--res 1536] crop.png ...
"""
import argparse, json, os, sys, time

os.environ.setdefault('ATTN_BACKEND', 'flash_attn_3')
CODE = os.environ.get('TRELLIS2_CODE', '/content/ext/TRELLIS.2')
W = os.environ.get('TRELLIS2_W', '/content/w/TRELLIS.2-4B')
sys.path.insert(0, CODE)
import numpy as np                                 # noqa: E402
import torch                                       # noqa: E402
import trimesh                                     # noqa: E402
from PIL import Image                              # noqa: E402
from trellis2.pipelines import Trellis2ImageTo3DPipeline   # noqa: E402

SHAPE_MODELS = ('sparse_structure_flow_model', 'sparse_structure_decoder', 'shape_slat_flow_model_512',
                'shape_slat_flow_model_1024', 'shape_slat_decoder')


def patched_config():
    cfg = json.load(open(f'{W}/pipeline.json'))
    a = cfg['args']
    a['rembg_model']['args']['model_name'] = 'ZhengPeng7/BiRefNet'
    a['image_cond_model']['args']['model_name'] = 'camenduru/dinov3-vitl16-pretrain-lvd1689m'
    a['models'] = {k: v for k, v in a['models'].items() if k in SHAPE_MODELS}
    json.dump(cfg, open(f'{W}/pipeline_shape.json', 'w'), indent=1)
    return 'pipeline_shape.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True); ap.add_argument('--seeds', default='42,7')
    ap.add_argument('--res', type=int, default=1536); ap.add_argument('--max_faces', type=int, default=400000)
    ap.add_argument('crops', nargs='+')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    p = Trellis2ImageTo3DPipeline.from_pretrained(W, patched_config())
    p.low_vram = False
    p.cuda()
    print(f'[probe] pipeline ready in {time.time() - t0:.0f} s', flush=True)
    log = open(os.path.join(a.out, 'gen_log.jsonl'), 'a')
    for crop in a.crops:
        tag = os.path.splitext(os.path.basename(crop))[0]
        img = p.preprocess_image(Image.open(crop).convert('RGBA'))
        for seed in [int(x) for x in a.seeds.split(',')]:
            t1 = time.time()
            rec = dict(model='trellis2', tag=tag, seed=seed, res=a.res, crop=crop)
            try:
                torch.manual_seed(seed)
                cond_512 = p.get_cond([img], 512)
                cond_1024 = p.get_cond([img], 1024)
                coords = p.sample_sparse_structure(cond_512, 32, 1, {})
                shape_slat, res = p.sample_shape_slat_cascade(
                    cond_512, cond_1024, p.models['shape_slat_flow_model_512'], p.models['shape_slat_flow_model_1024'],
                    512, a.res, coords, {}, 49152)
                meshes, _ = p.decode_shape_slat(shape_slat, res)
                m = meshes[0]
                m.fill_holes()
                rec['faces_raw'] = int(m.faces.shape[0]); rec['res_used'] = int(res)
                if m.faces.shape[0] > a.max_faces:
                    m.simplify(a.max_faces)
                v = m.vertices.detach().float().cpu().numpy().astype(np.float64)
                f = m.faces.detach().cpu().numpy().astype(np.int64)
                path = os.path.join(a.out, f'{tag}_s{seed}.ply')
                trimesh.Trimesh(v, f, process=False).export(path)
                rec.update(ok=True, faces=int(len(f)), extent=(v.max(0) - v.min(0)).round(4).tolist(), path=path)
            except Exception as e:
                rec.update(ok=False, error=repr(e)[:500])
            rec['sec'] = round(time.time() - t1, 1)
            print(json.dumps(rec), flush=True); log.write(json.dumps(rec) + '\n'); log.flush()
            torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
