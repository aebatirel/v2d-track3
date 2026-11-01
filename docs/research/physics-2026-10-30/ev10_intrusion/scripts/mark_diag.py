import json, sys
p = sys.argv[1]; H = json.load(open(p))
D = ('DIAGNOSTIC, NOT CONTRACT-VALID (ev10_intrusion/scripts/intrusion_diag.py: provenance deny-list hits recorded, not enforced; '
     'push phase stopped, pushes for selected frames in push_B_selected.txt)')
if 'DIAGNOSTIC' not in H:
    H = dict(DIAGNOSTIC=D, **H); H['flags'] = [D] + H['flags']
    json.dump(H, open(p, 'w'), indent=1); print('marked', p)
