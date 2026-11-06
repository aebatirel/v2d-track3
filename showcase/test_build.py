"""CPU check: build each showcase embodiment alone (FlashCHORD venv, from the flash_chord dir). test_build.py ROBOT..."""
import os, sys
import numpy as np
from hydra import compose, initialize_config_dir
import newton, warp as wp
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
for robot in sys.argv[1:]:
    with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
        cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f'embodiment={robot}'])
    emb = instantiate_typed(cfg.embodiment, Embodiment)
    b = newton.ModelBuilder(); lay = emb.build(b)
    m = b.finalize(device='cpu')
    h = lay.hand('right')
    mass = m.body_mass.numpy()
    print(f"{robot}: bodies {m.body_count} shapes {m.shape_count} | right: {len(h.finger_dof_ids)} fingers {list(h.finger_joint_names)[:4]}..., "
          f"contact links {h.contact_link_count}, tips {len(h.fingertip_frames)}, total mass {mass.sum():.2f} kg", flush=True)
