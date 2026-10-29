"""Per-hold contact shares by digit with the CORRECT slot labels (mkref PROBE_SITES order), next to the share the
earlier census / audits reported under the reference's mano_link_names labels (MANO link order, which does not describe
mkref's slots: slot_order_check.py). Our reference only. Usage: python -I digit_shares.py TAG=REF.parquet ...
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_ref, hold_list, SLOTS  # noqa: E402

DIG = {'thumb': [0, 5, 10], 'index': [1, 6, 11], 'middle': [2, 7, 12], 'ring': [3, 8, 13], 'pinky': [4, 9, 14], 'palm': [15]}
MANO = ['palm', 'thumb1', 'thumb2', 'thumb3', 'index1', 'index2', 'index3', 'middle1', 'middle2', 'middle3',
        'ring1', 'ring2', 'ring3', 'pinky1', 'pinky2', 'pinky3']
MDIG = {g: [i for i, n in enumerate(MANO) if n.startswith(g)] for g in DIG}
for spec in sys.argv[1:]:
    tag, path = spec.split('=', 1); d = load_ref(path)
    for ph in hold_list(path):
        if ph['end'] - ph['start'] < 15:
            continue
        s, o, a, b = ph['hand'], ph['object'], ph['start'], ph['end']; j = d['names'].index(o)
        on = d[f'pid_{s}'][a:b] == j + 1
        cor = {g: float(on[:, ks].any(1).mean()) for g, ks in DIG.items()}
        old = {g: float(on[:, ks].any(1).mean()) for g, ks in MDIG.items()}
        print(f"{tag:6s} {s[0]} {o[:13]:13s} {a:3d}-{b:3d} correct: " + ' '.join(f'{g} {v:.2f}' for g, v in cor.items())
              + ' | as labelled before: ' + ' '.join(f'{g} {v:.2f}' for g, v in old.items()))
