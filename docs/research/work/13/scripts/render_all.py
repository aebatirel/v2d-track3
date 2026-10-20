import sys; sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
from render_scan import load, face_colors, render
from PIL import Image, ImageDraw
names = sys.argv[1].split(",")
views = ["+x", "-x", "+y", "-y", "+z", "-z"]
for name in names:
    m = load(name); fc = face_colors(m)
    ims = [render(m, v, size=380, cols=fc) for v in views]
    canvas = Image.new("RGB", (380 * 6, 380))
    for k, (i, v) in enumerate(zip(ims, views)):
        ImageDraw.Draw(i).text((6, 6), f"{name} from {v}", fill=(255, 255, 0)); canvas.paste(i, (380 * k, 0))
    canvas.save(f"/Users/aebatirel/Documents/Code/v2d-research/work/13/render/six_{name}.jpg")
    print(name)
