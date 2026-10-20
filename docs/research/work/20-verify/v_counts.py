import cv2, pandas as pd, os
D3 = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3'
bad = []
for split, eps in (('public', [0,2,11,12,13,18,21,22,23,24,26,27,31,39,40,41,42,43,44,45]), ('evaluation', [1,3,5,6,8,10,14,15,16,19,20,25,28,30,32,33,35,36,37,38])):
    for ep in eps:
        n = {c: int(cv2.VideoCapture(f'{D3}/{split}/videos/chunk-000/observation.images.ego_cam_{c}/episode_{ep:06d}.mp4').get(cv2.CAP_PROP_FRAME_COUNT)) for c in 'abc'}
        rows = len(pd.read_parquet(f'{D3}/public/data/chunk-000/episode_{ep:06d}.parquet', columns=['frame_index'])) if split == 'public' else None
        fps = cv2.VideoCapture(f'{D3}/{split}/videos/chunk-000/observation.images.ego_cam_a/episode_{ep:06d}.mp4').get(cv2.CAP_PROP_FPS)
        if len(set(n.values())) > 1 or (rows is not None and rows != n['a']): bad.append((split, ep, n, rows))
print('mismatches:', bad)
