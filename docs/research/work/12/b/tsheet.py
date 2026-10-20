"""tsheet.py tag x0 y0 x1 y1 scale cols out : grid of fixed crops from work/12/frames/<tag>_*.jpg (2 fps samples)."""
import sys, glob
from PIL import Image, ImageDraw
tag = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); s = float(sys.argv[6]); cols = int(sys.argv[7]); out = sys.argv[8]
fs = sorted(glob.glob(f'/Users/aebatirel/Documents/Code/v2d-research/work/12/frames/{tag}_*.jpg'))
W, H = int((x1 - x0) * s), int((y1 - y0) * s); rows = (len(fs) + cols - 1) // cols
sh = Image.new('RGB', (cols * W, rows * H), 'black')
for i, f in enumerate(fs):
    im = Image.open(f).crop((x0, y0, x1, y1)).resize((W, H), Image.LANCZOS)
    ImageDraw.Draw(im).text((4, 4), f.split('/')[-1][:-4], fill=(255, 0, 0))
    sh.paste(im, ((i % cols) * W, (i // cols) * H))
sh.save(out, quality=88); print(out, sh.size, len(fs))
