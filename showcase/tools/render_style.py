"""Styled render of a showcase scene with FlashCHORD's own GL viewer (CPU or GPU): either the reference played
kinematically (no physics) or a recorded rollout trace (tools/trace_rollout.py npz: body poses per frame).
Colours are set to look like the real scene: white objects, a wooden table, a light floor, one colour per robot.
Run from the flash_chord dir with its venv (CPU: under xvfb-run).
  render_style.py PARQUET OUT.mp4 --emb EMB [--trace TRACE.npz] [--frames A:B] [--eye x,y,z] [--target x,y,z]
                  [--size 960x720] [--robot_rgb r,g,b] [--device cpu|cuda]
"""
import argparse, os

import numpy as np

p = argparse.ArgumentParser(); p.add_argument('parquet'); p.add_argument('out'); p.add_argument('--emb', default='sharpa_hands_mid')
p.add_argument('--trace', default=''); p.add_argument('--frames', default='')
p.add_argument('--eye', default='0.35,-0.95,1.15'); p.add_argument('--target', default='-0.08,-0.15,0.72')
p.add_argument('--size', default='960x720'); p.add_argument('--robot_rgb', default='0.30,0.33,0.38')
p.add_argument('--object_rgb', default='0.94,0.94,0.92'); p.add_argument('--table_rgb', default='0.58,0.34,0.18')
p.add_argument('--ground_rgb', default='0.82,0.83,0.85'); p.add_argument('--bg_rgb', default='0.95,0.96,0.97')
p.add_argument('--ego', default='', help='REFDIR,PERCDIR: render from the head camera (camera a) path of the video')
p.add_argument('--device', default='cpu'); a = p.parse_args()
rgb = lambda s: tuple(float(x) for x in s.split(','))

import warp as wp
if a.device == 'cpu':                     # no CUDA: the GL viewer asks for pinned host buffers; plain ones work
    for _n in ('empty', 'zeros'):
        _f = getattr(wp, _n)
        def _w(*x, _f=_f, **k):
            k.pop('pinned', None); return _f(*x, **k)
        setattr(wp, _n, _w)
from hydra import compose, initialize_config_dir
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.lifecycle.reset import reset_scene_to_frame
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
from flash_chord.visualization.viewer import ViewerConfig, configure_camera, configure_render_style, create_viewer

with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
    cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{a.parquet}'", f'embodiment={a.emb}'])
W, H = [int(x) for x in a.size.split('x')]
with wp.ScopedDevice(a.device):
    st = setup_scene(parquet=a.parquet, control_fps=20.0, motion_speed=1.0, embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                     collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True, decompose_objects=False)
    sc = st.scene; m = sc.model
    Q = np.load(a.trace)['q'] if a.trace else None
    n_all = len(Q) if Q is not None else st.reference.num_frames
    f0, f1 = (0, n_all) if not a.frames else [int(x) for x in a.frames.split(':')]
    vc = ViewerConfig(backend='mp4', output_path=a.out, num_frames=f1 - f0, headless=True, realtime=False, width=W, height=H,
                      camera_position=rgb(a.eye), camera_target=rgb(a.target), background_color=rgb(a.bg_rgb),
                      support_color=rgb(a.table_rgb), ground_color=rgb(a.ground_rgb), draw_shadows=True)
    viewer = create_viewer(vc, a.device); viewer.set_model(m); configure_camera(viewer, vc)
    configure_render_style(viewer, vc, sc)
    col = m.shape_color.numpy().copy(); body = m.shape_body.numpy()
    obj_shapes = set()
    for ob in sc.objects:
        obj_shapes.update(range(ob.shapes.start, ob.shapes.stop))
    labels = list(getattr(m, 'body_label', []) or [])
    for s in range(len(col)):
        b = int(body[s])
        if s in obj_shapes:
            col[s] = rgb(a.object_rgb)
        elif b >= 0 and b < len(labels) and str(labels[b]).split('/')[-1].startswith(('left_', 'right_')):
            col[s] = rgb(a.robot_rgb)
    m.shape_color.assign(wp.array(col, dtype=wp.vec3))
    state = m.state()
    ego = None
    if a.ego:                                 # sim_T_camA = T_table_from_world @ world_T_cam @ inv(T_rect_a); no roll (Newton camera)
        import math
        rd, pd = a.ego.split(',')
        Tt = np.load(f'{rd}/table_frame.npz')['T_table_from_world']; WC = np.load(f'{pd}/poses.npz')['world_T_cam'].astype(float)
        hz = np.load(f'{rd}/hands.npz'); Tra = np.linalg.inv(hz['T_rect_a'].astype(float)); fy = float(hz['Ka'][1, 1]); Ha = float(hz['size_a'][1])
        viewer.camera.fov = math.degrees(2 * math.atan(Ha / 2 / fy))
        ego = [Tt @ WC[min(k, len(WC) - 1)] @ np.linalg.inv(Tra) for k in range(n_all)]
    for i, f in enumerate(range(f0, f1)):
        if ego is not None:
            T = ego[f]; pos = T[:3, 3]; fwd = T[:3, 2] / np.linalg.norm(T[:3, 2])
            viewer.set_camera(wp.vec3(*pos.astype(float)), math.degrees(math.asin(fwd[2])), math.degrees(math.atan2(fwd[1], fwd[0])))
        if Q is not None:
            state.body_q.assign(wp.array(Q[f].astype(np.float32), dtype=wp.transform))
        else:
            reset_scene_to_frame(sc, st.reference, f, state)
        viewer.begin_frame(i / 20.0); viewer.log_state(state); viewer.end_frame()
    if hasattr(viewer, 'close'):
        viewer.close()
print(f'rendered {f1 - f0} frames -> {a.out}', flush=True)
