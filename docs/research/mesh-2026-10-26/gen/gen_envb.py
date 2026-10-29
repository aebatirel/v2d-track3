"""TripoSG (VAST-AI-Research/TripoSG, MIT) or Hunyuan3D-2.1 shape (Tencent-Hunyuan/Hunyuan3D-2.1, Tencent Hunyuan
community licence, research use only) on our RGBA crops (crops.py), single image, shape only.

Batch-2 generative probe, 2026-10-29. Runs on the box in env B (box_setup.sh). No background-removal model is loaded:
every crop carries its mask as alpha. Output: <out>/<crop tag>_s<seed>.ply in the generator's canonical frame
(arbitrary pose and scale; CD-O is similarity-invariant) and gen_log.jsonl.
Usage: gen_envb.py --model triposg|hy21 --out DIR [--seeds 42,7] crop.png ...
"""
import argparse, json, os, sys, time

import numpy as np
import torch
import trimesh


def load_triposg():
    code = os.environ.get('TRIPOSG_CODE', '/content/ext/TripoSG')
    sys.path[:0] = [code, os.path.join(code, 'scripts')]
    try:
        import diso  # noqa: F401
        flash = True
    except Exception:
        flash = False                                   # DiffDMC unavailable: hierarchical skimage extractor
        import types                                    # inference_utils imports diso unconditionally: stub it
        stub = types.ModuleType('diso')

        class DiffDMC:                                  # noqa: N801  only the flash decoder would call it
            def __init__(self, *a, **k):
                raise RuntimeError('diso is not installed')
        stub.DiffDMC = DiffDMC
        sys.modules['diso'] = stub
    from triposg.pipelines.pipeline_triposg import TripoSGPipeline
    from image_process import prepare_image
    pipe = TripoSGPipeline.from_pretrained(os.environ.get('TRIPOSG_W', '/content/w/TripoSG')).to('cuda', torch.float16)

    def run(crop, seed):
        img = prepare_image(crop, bg_color=np.array([1.0, 1.0, 1.0]), rmbg_net=None)
        out = pipe(image=img, generator=torch.Generator(device=pipe.device).manual_seed(seed), num_inference_steps=50,
                   guidance_scale=7.0, use_flash_decoder=flash).samples[0]
        return np.asarray(out[0], np.float64), np.ascontiguousarray(out[1])
    return run, dict(flash_decoder=flash)


def load_hy21():
    code = os.environ.get('HY21_CODE', '/content/ext/Hunyuan3D-2.1')
    sys.path.insert(0, os.path.join(code, 'hy3dshape'))
    os.environ.setdefault('HY3DGEN_MODELS', '/content/w/hy3dgen')
    from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
    pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained('tencent/Hunyuan3D-2.1')

    def run(crop, seed):
        from PIL import Image
        img = Image.open(crop).convert('RGBA')
        mesh = pipe(image=img, generator=torch.Generator('cuda').manual_seed(seed), num_inference_steps=50,
                    octree_resolution=384, num_chunks=20000, output_type='trimesh')[0]
        return np.asarray(mesh.vertices, np.float64), np.asarray(mesh.faces)
    return run, dict(octree_resolution=384)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True, choices=['triposg', 'hy21'])
    ap.add_argument('--out', required=True); ap.add_argument('--seeds', default='42,7')
    ap.add_argument('--max_faces', type=int, default=400000)
    ap.add_argument('crops', nargs='+')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    run, info = (load_triposg if a.model == 'triposg' else load_hy21)()
    print(f'[probe] {a.model} ready in {time.time() - t0:.0f} s {info}', flush=True)
    log = open(os.path.join(a.out, 'gen_log.jsonl'), 'a')
    for crop in a.crops:
        tag = os.path.splitext(os.path.basename(crop))[0]
        for seed in [int(x) for x in a.seeds.split(',')]:
            t1 = time.time()
            rec = dict(model=a.model, tag=tag, seed=seed, crop=crop, **info)
            try:
                with torch.no_grad():
                    v, f = run(crop, seed)
                m = trimesh.Trimesh(v, f, process=False)
                rec['faces_raw'] = int(len(m.faces))
                if len(m.faces) > a.max_faces:
                    import fast_simplification
                    v2, f2 = fast_simplification.simplify(m.vertices, m.faces, 1 - a.max_faces / len(m.faces))
                    m = trimesh.Trimesh(v2, f2, process=False)
                path = os.path.join(a.out, f'{tag}_s{seed}.ply')
                m.export(path)
                rec.update(ok=True, faces=int(len(m.faces)), extent=(m.vertices.max(0) - m.vertices.min(0)).round(4).tolist(),
                           path=path)
            except Exception as e:
                rec.update(ok=False, error=repr(e)[:500])
            rec['sec'] = round(time.time() - t1, 1)
            print(json.dumps(rec), flush=True); log.write(json.dumps(rec) + '\n'); log.flush()
            torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
