"""Compose the showcase video: the real head-camera clip on the left, up to 9 robot tiles (3 x 3) on the right, all on
one clock, each tile labelled with the robot, its fingers / joints and an optional score line (2026-11-06).
  grid_video.py OUT.mp4 --real REAL.mp4 --tiles TILES.json [--title TEXT] [--fps 20] [--frames N]
TILES.json: [{"video": path, "name": "Allegro Hand", "spec": "4 fingers, 16 joints", "score": "object error 0.9 cm"}, ...]
Output 1920x1080 H.264. ffmpeg only.
"""
import argparse, json, shlex, subprocess

p = argparse.ArgumentParser(); p.add_argument('out'); p.add_argument('--real', required=True); p.add_argument('--tiles', required=True)
p.add_argument('--title', default=''); p.add_argument('--fps', type=float, default=20); p.add_argument('--frames', type=int, default=0)
p.add_argument('--real_label', default='Real egocentric video (input)'); a = p.parse_args()
tiles = json.load(open(a.tiles))[:9]
W, H = 1920, 1080
TW, TH = (W - 760) // 3, (H - 60) // 3   # tile size (title bar 60 px)
LW = W - 3 * TW                          # left panel width (the rest)
esc = lambda s: s.replace('\\', '\\\\').replace(':', '\\:').replace("'", "’").replace('%', '\\%')
inputs = ['-i', a.real] + sum((['-i', t['video']] for t in tiles), [])
f = []
f.append(f"[0:v]fps={a.fps},scale={LW - 20}:-2,setsar=1[rs]")
f.append(f"color=c=0x101418:s={LW}x{H - 60}:r={a.fps}[lbg]")
f.append(f"[lbg][rs]overlay=(W-w)/2:(H-h)/2:shortest=1,drawtext=text='{esc(a.real_label)}':x=20:y=20:fontsize=26:fontcolor=white[left]")
for i, t in enumerate(tiles):
    lines = [t['name'], t.get('spec', ''), t.get('score', '')]
    d = f"[{i + 1}:v]fps={a.fps},scale={TW}:{TH}:force_original_aspect_ratio=increase,crop={TW}:{TH},setsar=1"
    d += f",drawbox=x=0:y=0:w={TW}:h=58:color=black@0.55:t=fill"
    d += f",drawtext=text='{esc(lines[0])}':x=10:y=6:fontsize=22:fontcolor=white"
    if lines[1]:
        d += f",drawtext=text='{esc(lines[1])}':x=10:y=32:fontsize=17:fontcolor=0xd0d6dc"
    if lines[2]:
        d += f",drawbox=x=0:y={TH - 30}:w={TW}:h=30:color=black@0.55:t=fill,drawtext=text='{esc(lines[2])}':x=10:y={TH - 25}:fontsize=18:fontcolor=0x9fe870"
    d += f",drawbox=x=0:y=0:w={TW}:h={TH}:color=0x101418:t=2[t{i}]"
    f.append(d)
for i in range(len(tiles), 9):
    f.append(f"color=c=0x101418:s={TW}x{TH}:r={a.fps}[t{i}]")
lay = '|'.join(f"{(i % 3) * TW}_{(i // 3) * TH}" for i in range(9))
f.append(''.join(f'[t{i}]' for i in range(9)) + f"xstack=inputs=9:layout={lay}:shortest=1[grid]")
f.append(f"[left][grid]hstack=inputs=2:shortest=1[body]")
f.append(f"color=c=0x0b0e11:s={W}x60:r={a.fps}[top]")
f.append(f"[top]drawtext=text='{esc(a.title)}':x=20:y=15:fontsize=28:fontcolor=white[topt]")
f.append(f"[topt][body]vstack=inputs=2:shortest=1,scale={W}:{H},format=yuv420p[out]")
cmd = ['ffmpeg', '-loglevel', 'error', '-y'] + inputs + ['-filter_complex', ';'.join(f), '-map', '[out]', '-r', str(a.fps)]
if a.frames:
    cmd += ['-frames:v', str(a.frames)]
cmd += ['-c:v', 'libx264', '-crf', '20', '-preset', 'medium', a.out]
r = subprocess.run(cmd)
if r.returncode:
    print(' '.join(shlex.quote(c) for c in cmd)); raise SystemExit(r.returncode)
print('wrote', a.out)
