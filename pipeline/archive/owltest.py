import json, sys, numpy as np, cv2, torch
from PIL import Image
from transformers import Owlv2Processor, Owlv2ForObjectDetection
D = '/content/t3'; EPS = [int(e) for e in sys.argv[1].split(',')]
P = {'pot': ['a pot', 'a white pot', 'a saucepan', 'a cooking pot', 'a pan'], 'lid': ['a lid', 'a pot lid'],
     'cup': ['a cup', 'a mug'], 'rack': ['a dish rack', 'a dish drainer', 'a plastic basket'],
     'pitcher': ['a pitcher', 'a jug'], 'sweeper': ['a hand broom', 'a brush', 'a small broom'],
     'pan': ['a dustpan', 'a dust pan', 'a scoop'], 'wood': ['a wooden block', 'a wooden plank', 'a piece of wood']}
Q = [q for v in P.values() for q in v]
C = json.load(open(f'{D}/calib.json')); cam = C['cameras']; sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float); D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
E = np.array(sp['left_to_right'], float)
R1, R2, P1, P2, _, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), (1280, 800), E[:3, :3], E[:3, 3:], alpha=0, newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
MC = cv2.initUndistortRectifyMap(K_('ego_cam_c'), D_('ego_cam_c'), R1, P1, (1600, 1000), cv2.CV_32FC1)
proc = Owlv2Processor.from_pretrained('google/owlv2-base-patch16-ensemble')
det = Owlv2ForObjectDetection.from_pretrained('google/owlv2-base-patch16-ensemble').cuda().eval()
pp = getattr(proc, 'post_process_grounded_object_detection', None) or proc.post_process_object_detection
for ep in EPS:
    ok, f = cv2.VideoCapture(f'{D}/v/ep{ep}_c.mp4').read()
    g = cv2.remap(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), MC[0], MC[1], cv2.INTER_LINEAR); im = np.repeat(g[..., None], 3, 2)
    inp = proc(text=[Q], images=Image.fromarray(im), return_tensors='pt').to('cuda')
    with torch.no_grad(): o = det(**inp)
    r = pp(outputs=o, threshold=0.01, target_sizes=torch.tensor([[1600, 1600]]).cuda())[0]
    vis = im.copy(); line = []
    for j, q in enumerate(Q):
        sel = (r['labels'] == j).nonzero().flatten()
        if len(sel) == 0: continue
        k = sel[r['scores'][sel].argmax()]; b = r['boxes'][k].cpu().numpy().astype(int); s = float(r['scores'][k])
        line.append(f'{q}:{s:.2f}@{b[0]},{b[1]},{b[2]},{b[3]}')
        if s > 0.1:
            cv2.rectangle(vis, tuple(b[:2]), tuple(b[2:]), (0, 0, 255), 2); cv2.putText(vis, f'{q} {s:.2f}', (b[0], b[1] + 18), 0, 0.6, (0, 0, 255), 2)
    print('EP', ep, ' | '.join(line), flush=True)
    cv2.imwrite(f'/content/owl_ep{ep}.jpg', cv2.resize(vis, (960, 600)))
