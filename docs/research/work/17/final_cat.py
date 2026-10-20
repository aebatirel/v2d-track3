"""Write the curated marker catalogue (scan frame, metres). Selection rule: normal-Hough sphere candidates with
coverage >= 0.6, rms <= 0.3 mm, sphere brighter than the 1.5-6 mm ring around it by > 0.1 (mount contrast);
plus one texture-only small marker on the lid (geometry flattened in the scan; centre estimated)."""
import json, numpy as np
C = json.load(open('out/cand_flat.json')); out = {}
for n, L in C.items():
    keep = []
    for q in L:
        if q['cov'] >= 0.6 and q['rms'] <= 0.0003 and (np.mean(q['col']) - np.mean(q['ring'])) > 0.1 and 0.003 < q['r'] < 0.0085:
            keep.append(dict(c=q['c'], r=q['r'], size='large' if q['r'] > 0.0055 else 'small', src='geometry', cov=q['cov'], rms=q['rms']))
    out[n] = keep
# lid small geometric marker is dark-ish (sphere poorly textured) -> rule above drops it; add explicitly
out['white_pot_lid'].append(dict(c=[0.0025, 0.0582, -0.0029], r=0.00408, size='small', src='geometry (dark texture)', cov=0.69, rms=0.00023))
out['white_pot_lid'].append(dict(c=[0.0056, -0.0128, -0.0473], r=0.0040, size='small', src='texture only; centre over mount, height +5.2 mm as the other small lid marker [E +-3 mm]', cov=0, rms=None))
out['wooden_spoon'] = 'no public scan; 3 markers in video (note 13: M1 near bowl, M2 handle side, M3 handle end)'
json.dump(out, open('out/marker_catalogue.json', 'w'), indent=1)
for n, L in out.items():
    if isinstance(L, str): print(n, L); continue
    M = np.array([q['c'] for q in L]); D = np.linalg.norm(M[:, None] - M[None], axis=2)
    iu = np.triu_indices(len(M), 1)
    print(f"{n}: {len(L)} markers ({sum(q['size']=='large' for q in L)} large, {sum(q['size']=='small' for q in L)} small); "
          f"r mm {[round(q['r']*1000,2) for q in L]}; pairwise dist mm min {D[iu].min()*1000:.0f} max {D[iu].max()*1000:.0f}; "
          f"min |d_i - d_j| between pair distances mm {np.min(np.abs(np.subtract.outer(D[iu], D[iu]))[np.triu_indices(len(iu[0]), 1)])*1000:.1f}" if len(L) > 2 else '')
