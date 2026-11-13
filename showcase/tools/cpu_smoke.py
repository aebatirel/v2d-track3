"""CPU smoke test of FlashCHORD training with a showcase embodiment (catches integration errors before GPU rental).
Run from the flash_chord dir with its venv: cpu_smoke.py <train_flash_sac overrides...>
Warp graph capture crashes on the CPU (work log 2026-10-31), so the transition is stepped eagerly there."""
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from flash_chord.envs.rl import RLEnv
_cap0 = RLEnv.capture_step
def _capture_step(self):
    if not self.device.is_cpu:
        _cap0(self)
RLEnv.capture_step = _capture_step
import train_flash_sac as t
t.main.__wrapped__.__module__ = '__main__'
t.main()
