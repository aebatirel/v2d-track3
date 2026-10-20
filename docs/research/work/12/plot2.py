"""Per-object spin self-similarity curves (PIL): geometry mean NN (mm) and spin-specific texture correlation."""
import numpy as np, json, os
from PIL import Image
from plot import lineplot
names = ['blue_cup', 'beige_cup', 'white_pot_lid', 'white_pot', 'water_pitcher']
tiles = []
for n in names:
    r2 = json.load(open(f'out/symm2_{n}.json'))
    lineplot([('geo with markers', np.array(r2['all']['geo']) * 1000, (31, 119, 180)), ('geo markers removed', np.array(r2['nomk']['geo']) * 1000, (255, 127, 14))],
             f'out/_g_{n}.png', W=480, H=220, title=f'{n}: geometry mean NN dist (mm) vs spin (deg)')
    row = [Image.open(f'out/_g_{n}.png')]
    if os.path.exists(f'out/symm3_{n}.json'):
        r3 = json.load(open(f'out/symm3_{n}.json'))
        c1 = (np.array(r3['all']) + 1) / 2; c2 = (np.array(r3['nomk']) + 1) / 2   # map [-1,1] -> [0,1]
        lineplot([('tex with markers', c1, (31, 119, 180)), ('tex markers removed', c2, (255, 127, 14)), ('corr = 0', np.full(len(c1), 0.5), (150, 150, 150))],
                 f'out/_t_{n}.png', W=480, H=220, title=f'{n}: (1+corr)/2 of spin-specific colour detail', ymax=1.0)
        row.append(Image.open(f'out/_t_{n}.png'))
    tiles.append(row)
W = 960; H = 220 * len(tiles); im = Image.new('RGB', (W, H), 'white')
for i, row in enumerate(tiles):
    for j, t in enumerate(row): im.paste(t, (480 * j, 220 * i))
im.save('out/spin_selfsim_curves.png'); print('saved')
