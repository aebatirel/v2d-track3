"""Render a recorded rollout (tools/trace_rollout.py npz: body poses per frame) with FlashCHORD's own mp4 viewer, from
a chosen camera (e.g. a close-up of a grasp). The scene is built from the same reference parquet; no physics is run.
Usage (FlashCHORD python, from the flash_chord dir): render_trace.py PARQUET TRACE.npz OUT.mp4
       [--frames A:B] [--target x,y,z] [--eye x,y,z] [--size 960x540]
"""
import argparse, os

import numpy as np


def main():
    p = argparse.ArgumentParser(); p.add_argument('parquet'); p.add_argument('trace'); p.add_argument('out')
    p.add_argument('--frames', default=None); p.add_argument('--target', default='0,0,0.65'); p.add_argument('--eye', default='0.55,-0.45,1.05')
    p.add_argument('--size', default='960x540'); a = p.parse_args()
    import warp as wp
    from hydra import compose, initialize_config_dir
    from flash_chord.configuration import instantiate_typed
    from flash_chord.embodiments.base import Embodiment
    from flash_chord.scene.collision import CollisionPolicy
    from flash_chord.scene.setup import setup_scene
    from flash_chord.visualization.viewer import ViewerConfig, configure_camera, create_viewer
    with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
        cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{a.parquet}'"])
    d = np.load(a.trace); Q = d['q']; f0, f1 = (0, len(Q)) if not a.frames else [int(x) for x in a.frames.split(':')]
    W, H = [int(x) for x in a.size.split('x')]
    vc = ViewerConfig(backend='mp4', output_path=a.out, num_frames=f1 - f0, headless=True, realtime=False, width=W, height=H,
                      camera_position=tuple(float(x) for x in a.eye.split(',')), camera_target=tuple(float(x) for x in a.target.split(',')))
    with wp.ScopedDevice('cuda'):
        st = setup_scene(parquet=a.parquet, control_fps=20.0, motion_speed=1.0, embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                         collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True, decompose_objects=True)
        m = st.scene.model; viewer = create_viewer(vc, 'cuda'); viewer.set_model(m); configure_camera(viewer, vc); state = m.state()
        for i, f in enumerate(range(f0, f1)):
            state.body_q.assign(wp.array(Q[f].astype(np.float32), dtype=wp.transform))
            viewer.begin_frame(i / 20.0); viewer.log_state(state); viewer.end_frame()
        if hasattr(viewer, 'close'):
            viewer.close()
    print(f'rendered frames {f0}-{f1} -> {a.out}', flush=True)


if __name__ == '__main__':
    main()
