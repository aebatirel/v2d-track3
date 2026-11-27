"""Compose the final-pack eval videos (2026-11-27), ffmpeg only, 1920x1080 H.264, 20 fps.
  compose_eval.py episode EP OUT.mp4 [--out_dir /content/ev]   real video (left, large) | policy from the head-camera path
                                                               (top right) | side view (bottom right)
  compose_eval.py grid OUT.mp4 [--eps 1,3,...]                 all episodes: real | policy (head-camera path) pairs, 4 x 5
Inputs per episode (render_all.sh, compare_packed.py): OUT_DIR/ep<N>/render_{ego,side}.mp4, setup.json, the real video
/content/t3/eval/v/ep<N>_a.mp4 and results/replay_vs_packed_cpu.json (how far the replay is from the submitted rollout).
"""
import argparse, json, os, shlex, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
p = argparse.ArgumentParser(); p.add_argument('mode', choices=['episode', 'grid']); p.add_argument('a'); p.add_argument('b', nargs='?')
p.add_argument('--out_dir', default='/content/ev'); p.add_argument('--videos', default='/content/t3/eval/v')
p.add_argument('--eps', default='1,3,5,6,8,10,14,15,16,19,20,25,28,30,32,33,35,36,37,38'); p.add_argument('--fps', type=float, default=20)
a = p.parse_args()
NAMES = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'wooden_spoon': 'wooden spoon', 'beige_cup': 'beige cup', 'blue_cup': 'blue cup',
         'plastic_dish_rack': 'dish rack', 'mini_sweeper': 'hand brush', 'mini_dust_pan': 'dust pan', 'water_pitcher': 'pitcher',
         'wooden_piece_1': 'wooden board', 'wooden_piece_2': 'wooden board'}
CMP = json.load(open(f'{HERE}/results/replay_vs_packed_cpu.json'))
DIVERGED = {15: 'This CPU replay drops the spoon at 6.5 s. The rollout we submitted (GPU) kept it, as did all 10 official GPU runs.'}
esc = lambda s: s.replace('\\', '\\\\').replace(':', '\\:').replace("'", "’").replace('%', '\\%').replace(',', '\\,')
BG, BAR = '0x101418', '0x0b0e11'


def objects(ep):
    names = json.load(open(f'{a.out_dir}/ep{ep}/setup.json'))['objects']
    return ', '.join(dict.fromkeys(NAMES.get(n, n) for n in names))


def gap(ep):
    o = CMP[str(ep)]['objects']; return sum(v['mean_cm'] for v in o.values()) / len(o)


def run(inputs, f, out):
    cmd = ['ffmpeg', '-loglevel', 'error', '-y'] + inputs + ['-filter_complex', ';'.join(f), '-map', '[out]', '-r', str(a.fps),
                                                            '-c:v', 'libx264', '-crf', '20', '-preset', 'medium', '-pix_fmt', 'yuv420p', out]
    r = subprocess.run(cmd)
    if r.returncode:
        print(' '.join(shlex.quote(c) for c in cmd)); raise SystemExit(r.returncode)
    print('wrote', out)


if a.mode == 'episode':
    ep, out = int(a.a), a.b; D = f'{a.out_dir}/ep{ep}'
    W, H, T = 1920, 1080, 70
    RW, RH = 1230, 922                      # real video, 4:3
    SW, SH = 660, 495                       # sim tiles, 4:3
    inputs = ['-i', f'{a.videos}/ep{ep}_a.mp4', '-i', f'{D}/render_ego.mp4', '-i', f'{D}/render_side.mp4']
    title = f'Hidden test episode {ep} ({objects(ep)}): our final submitted policy'
    foot1 = 'Sharpa Wave hands. The policy was trained in physics on our reconstruction of this video; no motion capture was used.'
    foot2 = DIVERGED.get(ep, f'Shown: a CPU replay of the submitted policy. Its objects are {gap(ep):.1f} cm (mean) from the rollout we submitted.')
    f = [f"color=c={BG}:s={W}x{H}:r={a.fps}[bg]",
         f"[0:v]fps={a.fps},scale={RW}:{RH},setsar=1,drawbox=x=0:y=0:w={RW}:h=44:color=black@0.55:t=fill,"
         f"drawtext=text='{esc('Real head-camera video (input)')}':x=14:y=9:fontsize=26:fontcolor=white[r]",
         f"[1:v]fps={a.fps},scale={SW}:{SH},setsar=1,drawbox=x=0:y=0:w={SW}:h=40:color=black@0.55:t=fill,"
         f"drawtext=text='{esc('Policy in physics, from the head-camera path')}':x=12:y=8:fontsize=22:fontcolor=white[e]",
         f"[2:v]fps={a.fps},scale={SW}:{SH},setsar=1,drawbox=x=0:y=0:w={SW}:h=40:color=black@0.55:t=fill,"
         f"drawtext=text='{esc('Same rollout, side view')}':x=12:y=8:fontsize=22:fontcolor=white[s]",
         f"[bg][r]overlay=10:{T + 10}:shortest=1[x1]", f"[x1][e]overlay={20 + RW}:{T + 10}:shortest=1[x2]",
         f"[x2][s]overlay={20 + RW}:{T + 20 + SH}:shortest=1,"
         f"drawbox=x=0:y=0:w={W}:h={T}:color={BAR}:t=fill,drawtext=text='{esc(title)}':x=20:y=18:fontsize=30:fontcolor=white,"
         f"drawtext=text='{esc(foot1)}':x=20:y={T + RH + 22}:fontsize=21:fontcolor=0xd0d6dc,"
         f"drawtext=text='{esc(foot2)}':x=20:y={T + RH + 52}:fontsize=21:fontcolor={'0xffb74d' if ep in DIVERGED else '0x9fe870'}[out]"]
    run(inputs, f, out)
else:
    out = a.a; eps = [int(x) for x in a.eps.split(',')]
    W, H, T, FOOT = 1920, 1080, 70, 110
    COLS, ROWS = 4, 5; CW, CH = W // COLS, (H - T - FOOT) // ROWS          # 480 x 180 cells: real | sim, 240 x 180 each
    HW = CW // 2
    nmax = max(CMP[str(e)]['frames_packed'] for e in eps)
    inputs, f = [], [f"color=c={BG}:s={W}x{H}:r={a.fps}[bg0]"]
    for k, ep in enumerate(eps):
        inputs += ['-i', f'{a.videos}/ep{ep}_a.mp4', '-i', f'{a.out_dir}/ep{ep}/render_ego.mp4']
        n = min(CMP[str(ep)]['frames_packed'], CMP[str(ep)]['frames_replay'])
        pad = f"trim=end_frame={n},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={(nmax - n) / a.fps + 0.1:.2f}"
        f.append(f"[{2 * k}:v]fps={a.fps},{pad},scale={HW}:{CH},setsar=1[r{k}]")
        f.append(f"[{2 * k + 1}:v]fps={a.fps},{pad},scale={HW}:{CH},setsar=1[s{k}]")
        lab = f'eval {ep}'
        tag = f",drawbox=x={CW - 150}:y={CH - 26}:w=146:h=22:color=0xffb74d@0.85:t=fill,drawtext=text='{esc('replay differs')}':x={CW - 144}:y={CH - 23}:fontsize=16:fontcolor=black" if ep in DIVERGED else ''
        f.append(f"[r{k}][s{k}]hstack=inputs=2,drawbox=x=0:y=0:w=86:h=24:color=black@0.6:t=fill,drawtext=text='{esc(lab)}':x=6:y=3:fontsize=18:fontcolor=white"
                 f"{tag},drawbox=x=0:y=0:w={CW}:h={CH}:color={BG}:t=2[c{k}]")
    for k in range(len(eps)):
        x, y = (k % COLS) * CW, T + (k // COLS) * CH
        f.append(f"[bg{k}][c{k}]overlay={x}:{y}:eof_action=repeat[bg{k + 1}]")
    title = f'{len(eps)} hidden test videos, {len(eps)} robot policies: our final NVIDIA V2D Track 3 submission'
    l1 = 'In each pair: left, the real head-camera video; right, our policy for that video, trained in physics and seen from the same head path.'
    l2 = 'Sharpa Wave hands. No motion capture used. Leaderboard AUC 0.886 on these 20 episodes (scored by NVIDIA against hidden motion capture).'
    l3 = 'Eval 15: this replay drops the spoon; the rollout we submitted did not.' if any(e in DIVERGED for e in eps) else ''
    f.append(f"[bg{len(eps)}]drawbox=x=0:y=0:w={W}:h={T}:color={BAR}:t=fill,drawtext=text='{esc(title)}':x=20:y=18:fontsize=30:fontcolor=white,"
             f"drawtext=text='{esc(l1)}':x=20:y={H - FOOT + 14}:fontsize=21:fontcolor=0xd0d6dc,"
             f"drawtext=text='{esc(l2)}':x=20:y={H - FOOT + 44}:fontsize=21:fontcolor=0xd0d6dc"
             + (f",drawtext=text='{esc(l3)}':x=20:y={H - FOOT + 74}:fontsize=21:fontcolor=0xffb74d" if l3 else '')
             + f",trim=end_frame={nmax}[out]")
    run(inputs, f, out)
