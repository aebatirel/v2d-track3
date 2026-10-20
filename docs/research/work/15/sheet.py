"""Contact sheets from an ego clip. usage: sheet.py video out.png cols width rot frames|evenN|range:a:b:step"""
import sys, cv2, numpy as np
from PIL import Image, ImageDraw
vid, out, cols, W, rot, spec = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
cap = cv2.VideoCapture(vid); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
if spec.startswith('even'):
    k = int(spec[4:]); idx = [int(round(i*(n-1)/(k-1))) for i in range(k)]
elif spec.startswith('range:'):
    a,b,s = map(int, spec.split(':')[1:]); idx = list(range(a, min(b, n), s))
else:
    idx = [int(x) for x in spec.split(',')]
want = set(idx); got = {}; i = 0
while True:
    ok, fr = cap.read()
    if not ok: break
    if i in want:
        if rot: fr = cv2.rotate(fr, cv2.ROTATE_180)
        h = int(fr.shape[0]*W/fr.shape[1]); fr = cv2.resize(fr, (W, h), interpolation=cv2.INTER_AREA)
        got[i] = fr[:, :, ::-1] if fr.ndim == 3 else fr
    i += 1
    if i > max(idx): break
ims = [got[k] for k in idx if k in got]
h = ims[0].shape[0]; rows = (len(ims)+cols-1)//cols
canvas = Image.new('RGB', (cols*W, rows*h), (0,0,0)); d = ImageDraw.Draw(canvas)
for j,(k,im) in enumerate([(k,got[k]) for k in idx if k in got]):
    x, y = (j%cols)*W, (j//cols)*h
    canvas.paste(Image.fromarray(im).convert('RGB'), (x, y))
    d.rectangle([x, y, x+120, y+16], fill=(0,0,0)); d.text((x+3, y+2), f"f{k} t{k/20:.1f}s /{n}", fill=(255,255,0))
canvas.save(out); print(out, n, len(ims))
