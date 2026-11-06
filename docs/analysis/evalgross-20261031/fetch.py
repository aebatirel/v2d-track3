#!/usr/bin/env python3
"""Fetch the inference-side inputs of the eval gross-error screen (single-file hf_hub_download only, no listings).
Store aebatirel/v2d-store (HF dataset): pack-7 policy references, their feeding perception (poses.npz), table frames,
hands; organiser dataset nvidia/video_to_data_challenge: eval ego_cam_c videos + camera calibration.
No ground truth: no dataset parquet, no mocap, no scan is requested.
Usage: python3 -I fetch.py OUT_DIR [small|depth EP|video]"""
import json, os, sys, time
from huggingface_hub import hf_hub_download

OUT = sys.argv[1]; MODE = sys.argv[2] if len(sys.argv) > 2 else 'small'
STORE = 'aebatirel/v2d-store'; P6 = '20261026-pack6-5203d42'
# eval -> (policy reference path under the store, feeding perception run, base ref variant for the table frame)
REFS = {1: 'perc2mcks/ep1/processed/sequence_id=t3_ep001/robot_name=sharpa_wave/64333b0b8cec4bb397290b3ca3d6f399-0.parquet',
        19: 'perc2mcks/ep19/processed/sequence_id=t3_ep019/robot_name=sharpa_wave/afc53914ae7542d7b565119fc4892688-0.parquet',
        25: 'perc2mcks/ep25/processed/sequence_id=t3_ep025/robot_name=sharpa_wave/2057d9f10b3a421ebbfd847c1219d1a0-0.parquet',
        28: 'perc2mcks/ep28/processed/sequence_id=t3_ep028/robot_name=sharpa_wave/4327c2f4a8b7432f9128481b2d45c34f-0.parquet',
        30: 'perc2mcks/ep30/processed/sequence_id=t3_ep030/robot_name=sharpa_wave/a2eb7d276dd84fe6bed9251b46e93770-0.parquet'}
for e in (3, 5, 6, 8, 10, 14, 15, 16, 20, 32, 33, 35, 36, 37, 38):
    REFS[e] = f'glockt/ep{e}/processed/sequence_id=t3_ep{e:03d}/robot_name=sharpa_wave/ref_gl_ilc.parquet'
PERC = {e: P6 for e in REFS}
PERC.update({8: '20261025-evb0810-ee7ba8e', 14: '20261025-evb1420-ee7ba8e', 25: '20261026-c25s42-feb0407',
             30: '20261025-std30-ee7ba8e', 32: '20261026-fr32s46b-5e0e100', 33: '20261026-fr3233s43-6a8a0e2'})
BASE = {e: ('perc2mcks' if REFS[e].startswith('perc2mcks') else 'perc2mck') for e in REFS}
EPS = sorted(REFS)


def get(repo, path, rtype='dataset', tries=4):
    for k in range(tries):
        try:
            return hf_hub_download(repo, path, repo_type=rtype, local_dir=OUT, token='x')
        except Exception as ex:  # noqa: BLE001
            msg = str(ex).splitlines()[0][:200]
            if '404' in msg or 'Entry Not Found' in msg or 'EntryNotFound' in type(ex).__name__:
                return None
            time.sleep(5 * (k + 1))
    return None


def main():
    log = []
    if MODE == 'small':
        for e in EPS:
            src = {}
            src['ref'] = get(STORE, f'runs/{P6}/refs/{REFS[e]}') if e != 33 else (
                get(STORE, f'runs/20261030-c33B-0202139/refs/{REFS[e]}') or get(STORE, f'runs/{P6}/refs/{REFS[e]}'))
            src['poses'] = get(STORE, f'runs/{PERC[e]}/perc2/ep{e}/poses.npz')
            for v in (BASE[e], 'perc2mck', 'perc2mcks'):
                src['table'] = get(STORE, f'runs/{PERC[e]}/refs/{v}/ep{e}/table_frame.npz')
                if src['table']:
                    src['table_variant'] = v; break
            src['hands'] = get(STORE, f'runs/{PERC[e]}/refs/perc2mck/ep{e}/hands_refined.npz') or \
                get(STORE, f'runs/{PERC[e]}/refs/perc2mcks/ep{e}/hands_refined.npz')
            src['ep'] = e; src['perc_run'] = PERC[e]
            print(json.dumps(src), flush=True); log.append(src)
        cal = get('nvidia/video_to_data_challenge', 'track_3/public/meta/camera_calibration.json')
        log.append({'calib': cal})
        json.dump({'eps': log, 'refs': REFS, 'perc': PERC}, open(os.path.join(OUT, 'fetch_small.json'), 'w'), indent=1)
    elif MODE == 'depth':
        e = int(sys.argv[3])
        print(get(STORE, f'cache/depth/eval/ep{e}/depths_fs0.5.npy'), flush=True)
    elif MODE == 'video':
        for e in EPS:
            print(e, get('nvidia/video_to_data_challenge',
                         f'track_3/evaluation/videos/chunk-000/observation.images.ego_cam_c/episode_{e:06d}.mp4'), flush=True)


if __name__ == '__main__':
    main()
