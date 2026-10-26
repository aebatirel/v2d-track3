"""Image-to-3D with Hunyuan3D-2mini (turbo DiT + FlashVDM turbo VAE) on CPU or GPU, one RGBA crop -> one mesh.

Research probe for the mesh round of 2026-10-26: does a generative shape prior beat our TSDF meshes on CD-O?
Input: the RGBA crops of crops.py (object on transparent background). Output: <out>/<tag>_s<seed>.glb (canonical
generator frame, arbitrary scale; CD-O is similarity-invariant, so it can be scored as is) and a timing JSON.
Usage: gen_hy3d.py --code HUNYUAN3D2_REPO --models HY3DGEN_MODELS_DIR --out DIR [--device cpu] [--steps 5]
                   [--octree 256] [--seeds 0,1] crop1.png crop2.png ...
Licence: Tencent Hunyuan 3D 2.0 Community Licence (excludes the EU, UK and South Korea); research use here.
"""
import argparse, json, os, sys, time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--code', required=True); p.add_argument('--models', required=True)
    p.add_argument('--out', required=True); p.add_argument('--device', default='cpu')
    p.add_argument('--steps', type=int, default=5); p.add_argument('--octree', type=int, default=256)
    p.add_argument('--chunks', type=int, default=20000); p.add_argument('--seeds', default='0')
    p.add_argument('--subfolder', default='hunyuan3d-dit-v2-mini-turbo'); p.add_argument('--flashvdm', type=int, default=1)
    p.add_argument('--threads', type=int, default=4)
    p.add_argument('crops', nargs='+')
    a = p.parse_args()
    os.environ['HY3DGEN_MODELS'] = a.models
    sys.path.insert(0, a.code)
    import torch
    from PIL import Image
    torch.set_num_threads(a.threads)
    from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
    dtype = torch.float32 if a.device == 'cpu' else torch.float16
    t0 = time.time()
    pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained('tencent/Hunyuan3D-2mini', subfolder=a.subfolder,
                                                            device=a.device, dtype=dtype)
    if a.flashvdm:
        pipe.enable_flashvdm(mc_algo='mc')
        pipe.vae.to(a.device, dtype)
    print(f'loaded in {time.time() - t0:.0f} s', flush=True)
    os.makedirs(a.out, exist_ok=True)
    log = []
    for crop in a.crops:
        img = Image.open(crop).convert('RGBA')
        tag = os.path.splitext(os.path.basename(crop))[0]
        for s in [int(x) for x in a.seeds.split(',')]:
            t1 = time.time()
            with torch.no_grad():
                mesh = pipe(image=img, num_inference_steps=a.steps, octree_resolution=a.octree, num_chunks=a.chunks,
                            generator=torch.Generator(a.device).manual_seed(s), output_type='trimesh')[0]
            path = os.path.join(a.out, f'{tag}_s{s}.glb')
            mesh.export(path)
            rec = dict(crop=crop, seed=s, path=path, faces=int(len(mesh.faces)), sec=round(time.time() - t1, 1))
            log.append(rec); print(json.dumps(rec), flush=True)
    json.dump(log, open(os.path.join(a.out, 'gen_log.json'), 'a'), indent=1)


if __name__ == '__main__':
    main()
