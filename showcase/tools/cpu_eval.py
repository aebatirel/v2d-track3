"""CPU check of the official evaluator on a showcase checkpoint (rebuilds the embodiment from the checkpoint config).
Run from the flash_chord dir with its venv: cpu_eval.py <evaluate_policy overrides...>"""
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from flash_chord.envs.rl import RLEnv
_cap0 = RLEnv.capture_step
def _capture_step(self):
    if not self.device.is_cpu:
        _cap0(self)
RLEnv.capture_step = _capture_step
import evaluate_policy as e
e.main.__wrapped__.__module__ = '__main__'
e.main()
