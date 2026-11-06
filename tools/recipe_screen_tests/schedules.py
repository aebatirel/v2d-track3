"""CPU check of the recipe screen's arm settings in FlashCHORD's own config code (physics-solver.md section 8).
Composes train_flash_sac exactly as ops/jobs/recipe_screen.sh does (experiment=sharpa_flash_sac, the box's FDR
TRAIN_ARGS, the arm's overrides from tools/recipe_screen.py), instantiates the FlashSAC TrainingConfig, and prints
  - the optimizer horizon (total_optimizer_updates, learning_rate_schedule_updates) and the learning rates at
    10M..70M environment steps on the critic clock (every update) and on the actor / temperature clock (one update in
    actor_update_period = 2), through flash_chord.training.flash_sac.update.learning_rate itself;
  - the curriculum's VOC scale at every 5M steps and at each saved checkpoint, and the stage boundaries;
  - the resolved-config differences between the arms (C vs D must be none);
  - what the evaluator does with each arm's config (harness.apply_evaluation_composition + the evaluation stage).
Run from a FlashCHORD dir whose package has the box patches (FDR writes the v2d curriculum):
  python schedules.py PATCHED_FC_DIR REF_TASK_DIR OUT.json"""
import copy, json, math, os, sys

FCD, TASK, OUT = sys.argv[1:4]
sys.path.insert(0, os.path.join(FCD, 'src'))
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import recipe_screen as RS  # noqa: E402
from hydra import compose, initialize_config_dir  # noqa: E402
from omegaconf import OmegaConf  # noqa: E402

from flash_chord.configuration import instantiate_typed  # noqa: E402
from flash_chord.training.flash_sac.config import TrainingConfig  # noqa: E402
from flash_chord.training.flash_sac.update import learning_rate  # noqa: E402
from flash_chord.evaluation import harness  # noqa: E402

STEPS = 70004736
FDR = 'curriculum=tracking_250m_mixed_reset_v2d objective.force_closure.enabled=true objective.force_closure.weight=6 ' \
      'objective.contact_wrench_support.weight=3 objective.unintended_contact.weight=-2'.split()   # ops/box/lib.sh FDR_TRAIN_ARGS
CKPTS = [10002432, 20000768, 30003200, 40001536, 50003968, 60002304, 70004736]   # FlashCHORD's save points (10000384 apart)
res = dict(arms={})
with initialize_config_dir(version_base='1.3', config_dir=os.path.join(FCD, 'src/flash_chord/configs')):
    cfgs = {}
    for arm in RS.ARMS:
        ov = ['experiment=sharpa_flash_sac', 'embodiment=sharpa_hands_mid', f"task.parquet='{TASK}'", 'task.motion_speed=1.0',
              'reset.seed=42', 'logging.mode=disabled', 'output_dir=/x/run', f'training.total_environment_steps={STEPS}'] + FDR \
            + RS.arm_overrides(arm, STEPS)
        cfgs[arm] = compose(config_name='train_flash_sac', overrides=ov)
yaml_thr = list(OmegaConf.to_container(cfgs['C'].curriculum, resolve=True)['thresholds'])
res['v2d_curriculum_thresholds_equal_tool_constant'] = yaml_thr == RS.THRESHOLDS
res['v2d_curriculum_voc'] = [float(s['voc_scale']) for s in OmegaConf.to_container(cfgs['C'].curriculum, resolve=True)['stages']]
res['voc_constant_matches'] = res['v2d_curriculum_voc'] == RS.VOC
print('v2d curriculum thresholds == tools/recipe_screen.py THRESHOLDS:', res['v2d_curriculum_thresholds_equal_tool_constant'],
      '| stage VOC', res['v2d_curriculum_voc'])
c_min = cfgs['C'].training.replay.minimum_size
for arm, cfg in cfgs.items():
    tc = instantiate_typed(cfg.training, TrainingConfig)
    o = tc.optimization; H = tc.learning_rate_schedule_updates
    # global optimizer updates after s environment steps: updates_per_collection per 4,096-world collection once the
    # replay holds minimum_size transitions (+ n_step - 1 pending) [E: +-0.1 % of the horizon]
    warm = math.ceil(tc.replay.minimum_size / tc.world_count) + tc.replay.n_step - 1
    g = lambda s: max(0, int((s // tc.world_count - warm) * tc.updates_per_collection))  # noqa: E731
    lr = lambda step: float(learning_rate(step, o, H))  # noqa: E731
    rows = []
    for s in [10_000_000 * k for k in range(1, 7)] + [STEPS]:            # 10M..60M and the cap (70,004,736)
        rows.append(dict(env_steps=s, global_updates=g(s), critic_lr=lr(g(s)), actor_lr=lr(math.ceil(g(s) / o.actor_update_period))))
    cur = tc.curriculum
    voc = [(s, cur.stages[cur.stage_index(s)].voc_scale) for s in range(0, STEPS + 1, 5_000_000)]
    ck = [(s, cur.stage_index(s), cur.stages[cur.stage_index(s)].voc_scale) for s in CKPTS]
    bounds = [(int(t), cur.stages[min(i + 1, len(cur.stages) - 1)].voc_scale) for i, t in enumerate(cur.thresholds) if t <= 2.6e8]
    res['arms'][arm] = dict(total_optimizer_updates=tc.total_optimizer_updates, learning_rate_schedule_updates=H,
                            configured_schedule_updates=o.learning_rate_schedule_updates, schedule_steps=list(tc.schedule_steps),
                            lr_initial=o.learning_rate_initial, lr_peak=o.learning_rate_peak, lr_end=o.learning_rate_end,
                            actor_update_period=o.actor_update_period, lr=rows, voc_every_5M=voc, voc_at_checkpoints=ck,
                            stage_starts=bounds, thresholds=list(cur.thresholds), replay_warmup_collections=warm)
    print(f"\n{arm}: horizon {H} updates (configured {o.learning_rate_schedule_updates}, total {tc.total_optimizer_updates}); "
          f"LR initial/peak/end {o.learning_rate_initial}/{o.learning_rate_peak}/{o.learning_rate_end}; schedule steps {tc.schedule_steps}")
    for r in rows:
        print(f"  {r['env_steps'] / 1e6:5.1f}M  updates {r['global_updates']:6d}  critic LR {r['critic_lr']:.3e}  actor/temp LR {r['actor_lr']:.3e}")
    print('  VOC at checkpoints (steps, stage, VOC):', [(f'{s / 1e6:.0f}M', i, v) for s, i, v in ck])
    print('  stage starts (step -> VOC):', [(f'{t / 1e6:.2f}M', v) for t, v in bounds if t <= 1.3e8])
# resolved-config differences
flat = lambda d, p='': ({f'{p}{k}': v for kk, vv in d.items() for k, v in flat(vv, f'{kk}.').items()} if isinstance(d, dict) else {p[:-1]: d})  # noqa: E731
F = {a: flat(OmegaConf.to_container(c, resolve=True)) for a, c in cfgs.items()}
diff = lambda a, b: sorted(k for k in set(F[a]) | set(F[b]) if F[a].get(k) != F[b].get(k))  # noqa: E731
res['config_diff_C_D'] = diff('C', 'D'); res['config_diff_C_K'] = diff('C', 'K')
print('\nresolved config C vs D differs in:', res['config_diff_C_D'] or 'nothing')
print('resolved config C vs K differs in:', res['config_diff_C_K'])
# what the evaluator does with the K config (the scored rollout's composition)
ev = {}
for arm in ('C', 'K'):
    c = copy.deepcopy(OmegaConf.to_container(cfgs[arm], resolve=True))
    harness.apply_evaluation_composition(c, world_count=1, reset_mode='explicit')
    tc = instantiate_typed(OmegaConf.create(c).training, TrainingConfig)
    st = [harness._evaluation_curriculum_stage(s, 'explicit').voc_scale for s in tc.curriculum.stages]
    ev[arm] = dict(env_voc_scale=c['env']['voc_scale'], voc_max_force=c['env']['voc']['max_force'], voc_max_torque=c['env']['voc']['max_torque'],
                   voc_decay_steps=c['env']['reset']['voc_decay_steps'], always_first_frame=c['env']['reset']['always_reset_to_first_frame'],
                   reset_seed=c['env']['reset']['seed'], auto_reset=c['env']['auto_reset'], eval_stage_voc=sorted(set(st)),
                   training_config_valid=True)
res['evaluator_composition'] = ev
print('evaluator composition per arm:', json.dumps(ev))
json.dump(res, open(OUT, 'w'), indent=1)
