"""Inside the image: for each episode, resolve the evaluator inputs the way evaluate_checkpoint does (checkpoint config
-> _resolve_parquet with the episode's --source-root -> load_reference -> object URDFs, support USDA) and check that
every resolved file lies inside that episode's input tree. CPU only, no simulation, no network."""
import hashlib, json, re, sys
from pathlib import Path
from flash_chord.data import load_reference
from flash_chord.assets.registry import support_usda_for_reference
from flash_chord.evaluation.harness import _resolve_parquet
from flash_chord.training.checkpoint import read_checkpoint_metadata
from flash_chord.training.checkpoint_metadata import checkpoint_config
sub = Path('/submission'); m = json.loads((sub / 'submission.json').read_text())['submissions'][0]
bad = 0; out = {}
for ep, ck in sorted(m['checkpoints'].items(), key=lambda x: int(x[0])):
    tree = (sub / m['eval_inputs'] / f'episode_{int(ep):06d}' / 'assets').resolve()
    cfg = checkpoint_config(read_checkpoint_metadata(sub / ck))
    parquet = _resolve_parquet(cfg, tree)
    ref = load_reference(parquet, control_fps=cfg['env']['sim']['fps'], motion_speed=cfg['task']['motion_speed'])
    urdfs = [a.urdf_path for a in ref.object_assets()]
    meshes = []
    for u in urdfs:
        for f in re.findall(r'filename="([^"]+)"', Path(u).read_text()):
            meshes.append(str((Path(u).parent / f).resolve()))
    support = support_usda_for_reference(ref)
    files = [parquet, *urdfs, *meshes, str(support)]
    outside = [f for f in files if not Path(f).resolve().is_relative_to(tree) or not Path(f).is_file()]
    bad += bool(outside)
    out[ep] = dict(parquet=parquet, urdfs=urdfs, n_meshes=len(meshes), support=str(support), frames=ref.num_frames,
                   saved_frames=cfg['reference']['num_frames'], outside=outside)
    print(f'ep {ep:>2}: {len(files)} files resolved, {"ALL inside the episode tree" if not outside else "OUTSIDE: " + str(outside[:3])}; '
          f'frames {ref.num_frames} (checkpoint {cfg["reference"]["num_frames"]}); urdfs {[Path(u).name for u in urdfs]}')
json.dump(out, open('/vout/check_inputs.json', 'w'), indent=1)
print('episodes with a file outside their tree or missing:', bad)
sys.exit(1 if bad else 0)
