"""refcheck/systematics, check 2 (frame bookkeeping; no ground truth needed except the mocap row count / timestamps).

For every canonical episode: mocap rows and timestamp step (public parquet), perception frames, reference frames
(final and pre-contact-retarget), and for every stored rollout of the canonical results dir: step count, whether
reference_frame == step (motion_speed 1.0 means one reference frame per control step), start_frame, control fps,
and whether the rollout's reference columns cover frames 0..T-1 in order.
Usage: python -I timecheck.py OUT.json
"""
import glob, json, os, sys
import numpy as np
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sysload import STORE, T3, canon, ref_files, load_ref_parquet, load_npz  # noqa: E402


def main():
    out = {}
    for ep, e in sorted(canon().items()):
        tab = pq.read_table(f'{T3}/ep{ep}.parquet', columns=['timestamp', 'frame_index', 'capture_time']).to_pandas()
        dt = np.diff(tab.timestamp.values)
        row = dict(mocap_rows=int(len(tab)), frame_index_is_0_to_T=bool((tab.frame_index.values == np.arange(len(tab))).all()),
                   mocap_dt_s=round(float(np.median(dt)), 6), mocap_fps=round(float(1 / np.median(dt)), 3),
                   mocap_dt_max_over_min=round(float(dt.max() / dt.min()), 4),
                   capture_minus_timestamp_s=[round(float(x), 4) for x in np.percentile(tab.capture_time - tab.timestamp, [0, 50, 100])])
        P = load_npz(f"{STORE}/{e['perception_path']}")
        row['perception_frames'] = int(len(P[next(iter(P))]))
        fin, pre, _ = ref_files(e)
        if fin:
            R = load_ref_parquet(fin); row['reference_frames'] = int(len(next(iter(R.values()))))
            if pre:
                R = load_ref_parquet(pre); row['pre_cr_reference_frames'] = int(len(next(iter(R.values()))))
            rf = pq.read_table(fin).column_names
            row['reference_fps_column'] = [c for c in rf if 'fps' in c.lower()]
        rolls = []
        if e.get('results_dir'):
            for f in sorted(glob.glob(f"{STORE}/{e['results_dir']}/r*/episode_*.parquet")):
                md = {k.decode(): v.decode() for k, v in (pq.read_schema(f).metadata or {}).items()}
                t = pq.read_table(f, columns=['step', 'reference_frame', 'object_body_name', 'environment_id']).to_pandas()
                g = t[t.environment_id == t.environment_id.min()]
                ok = all((gg.sort_values('step').reference_frame.values == np.arange(len(gg))).all() and
                         (gg.sort_values('step').step.values == np.arange(len(gg))).all()
                         for _, gg in g.groupby('object_body_name', observed=True))
                rolls.append(dict(file=f[len(STORE) + 1:], step_count=int(md.get('flash_chord.step_count', -1)),
                                  start_frame=int(md.get('flash_chord.start_frame', -1)),
                                  control_fps=float(md.get('flash_chord.control_fps', 'nan')),
                                  reference_frame_equals_step_0_to_T=bool(ok)))
        row['rollouts'] = rolls
        row['all_equal'] = bool(row['mocap_rows'] == row['perception_frames'] == row.get('reference_frames', row['mocap_rows'])
                                and all(r['step_count'] == row['mocap_rows'] and r['start_frame'] == 0 and r['reference_frame_equals_step_0_to_T'] for r in rolls))
        out[ep] = row
        print(ep, {k: v for k, v in row.items() if k != 'rollouts'}, len(rolls), 'rollouts')
    json.dump(out, open(sys.argv[1], 'w'), indent=1)


if __name__ == '__main__':
    main()
