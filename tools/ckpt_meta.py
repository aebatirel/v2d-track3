import json, sys
from safetensors import safe_open
for p in sys.argv[1:]:
    m = safe_open(p, 'np').metadata()
    c = json.loads(m['user.resolved_config_json'])
    print(p.split('/')[-1], 'steps', m.get('user.environment_steps'), 'stage', m.get('user.curriculum_stage'), 'voc', m.get('user.voc_scale'), 'p_first', m.get('user.reset_to_first_frame_probability'))
    print('  joint_overrides', c['embodiment']['config']['joint_overrides'])
    print('  action wrist_kp/tau_max', c['action'].get('wrist_kp'), c['action'].get('wrist_tau_max'), '| thresholds', c['curriculum'].get('thresholds'), '| motion_speed', c['task'].get('motion_speed'))
