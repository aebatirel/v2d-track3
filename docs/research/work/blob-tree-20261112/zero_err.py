"""Exercise 3 zero-residual replay; save per-frame object position error. Args: chord_workshop dir, out.npz"""
import importlib.util, sys, types
import numpy as np
d = sys.argv[1]; pkg = types.ModuleType('chord_workshop'); pkg.__path__ = [d]; sys.modules['chord_workshop'] = pkg
spec = importlib.util.spec_from_file_location('chord_workshop.simulation', f'{d}/simulation.py'); sim = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sim; spec.loader.exec_module(sim)
r = sim.Simulation().run(None, stop_on_failure=False)
np.savez_compressed(sys.argv[2], err=r.object_error, frames=r.frames); print('frames', len(r.err) if hasattr(r, 'err') else len(r.object_error))
