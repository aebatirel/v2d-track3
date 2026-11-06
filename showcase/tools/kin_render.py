"""Kinematic preview: play the reference (robot joints + objects) through FlashCHORD's own mp4 viewer, no physics.
Run from the flash_chord dir with its venv. kin_render.py PARQUET OUT.mp4 [--emb CFGNAME] [--frames N] [--eye] [--target]"""
import argparse, os, sys
import numpy as np
p = argparse.ArgumentParser(); p.add_argument('parquet'); p.add_argument('out'); p.add_argument('--emb', default='sharpa_hands')
p.add_argument('--frames', type=int, default=0); p.add_argument('--eye', default='0.9,-0.75,1.25'); p.add_argument('--target', default='0.0,0.0,0.72')
p.add_argument('--size', default='640x480'); p.add_argument('--confdir', default=''); p.add_argument('--device', default='cpu'); a = p.parse_args()
import warp as wp
if a.device == 'cpu':                     # no CUDA here: the GL viewer asks for pinned host buffers; plain ones work
    for _n in ('empty', 'zeros'):
        _f = getattr(wp, _n)
        def _w(*x, _f=_f, **k):
            k.pop('pinned', None); return _f(*x, **k)
        setattr(wp, _n, _w)
from hydra import compose, initialize_config_dir
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
from flash_chord.visualization.viewer import ViewerConfig, configure_camera, create_viewer
ov = ['experiment=sharpa_flash_sac', f"task.parquet='{a.parquet}'", f'embodiment={a.emb}']
if a.confdir: ov.append(f'hydra.searchpath=[file://{a.confdir}]')
with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
    cfg = compose(config_name='train_flash_sac', overrides=ov)
W, H = [int(x) for x in a.size.split('x')]
with wp.ScopedDevice(a.device):
    st = setup_scene(parquet=a.parquet, control_fps=20.0, motion_speed=1.0, embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                     collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True, decompose_objects=False)
    sc = st.scene; m = sc.model
    print('scene built; bodies', m.body_count, 'joints', m.joint_count, 'shapes', m.shape_count, flush=True)
    from flash_chord.lifecycle.reset import reset_scene_to_frame
    n = st.reference.num_frames if not a.frames else min(a.frames, st.reference.num_frames)
    vc = ViewerConfig(backend='mp4', output_path=a.out, num_frames=n, headless=True, realtime=False, width=W, height=H,
                      camera_position=tuple(float(x) for x in a.eye.split(',')), camera_target=tuple(float(x) for x in a.target.split(',')))
    viewer = create_viewer(vc, a.device); viewer.set_model(m); configure_camera(viewer, vc); state = m.state()
    for f in range(n):
        reset_scene_to_frame(sc, st.reference, f, state)
        viewer.begin_frame(f / 20.0); viewer.log_state(state); viewer.end_frame()
    if hasattr(viewer, 'close'): viewer.close()
    print('rendered', n, 'frames ->', a.out, flush=True)
