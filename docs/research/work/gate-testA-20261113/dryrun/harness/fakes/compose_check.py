"""DRY RUN ONLY: compose FlashCHORD's train_flash_sac config with the job's overrides (no training)."""
import sys
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf
fc, out, ov = sys.argv[1], sys.argv[2], sys.argv[3:]
with initialize_config_dir(config_dir=f'{fc}/src/flash_chord/configs', version_base='1.3'):
    cfg = compose(config_name='train_flash_sac', overrides=ov)
open(out, 'w').write(OmegaConf.to_yaml(cfg, resolve=False))
keys = ['task.parquet', 'task.motion_speed', 'reset.seed', 'training.total_environment_steps', 'output_dir',
        'objective.force_closure.enabled', 'objective.force_closure.weight', 'objective.contact_wrench_support.weight',
        'objective.unintended_contact.weight', 'sim.njmax', 'action.wrist_kp']
for k in keys:
    try:
        v = OmegaConf.select(cfg, k)
    except Exception as e:
        v = f'<unresolved: {type(e).__name__}>'
    print(f'{k} = {v}')
cur = cfg.get('curriculum')
print('curriculum stages =', len(cur.get('stages', [])) if cur is not None and hasattr(cur, 'get') else cur)
print('defaults/experiment chosen: embodiment =', OmegaConf.select(cfg, 'embodiment._target_', default='?'))
