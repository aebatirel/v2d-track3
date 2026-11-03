import json, sys
TAG = sys.argv[1]; EPS = [int(x) for x in sys.argv[2:]]; d = []
for e in EPS:
    c = json.load(open(f'diagC/Ct_ep{e}.json'))['perception']
    try: v = json.load(open(f'hrc/{TAG}_ep{e}.json'))['perception']
    except FileNotFoundError: print(e, 'missing'); continue
    lg = json.load(open(f'hrc/{TAG}/ep{e}/hrc.json'))['objects']
    d.append(v['AUC'] - c['AUC'])
    print(e, f"{c['AUC']:.4f} -> {v['AUC']:.4f} ({v['AUC'] - c['AUC']:+.4f})", {k: (x.get('corrected'), x.get('max_shift_cm')) for k, x in lg.items()})
print(TAG, 'mean dAUC %+.4f min %+.4f n %d' % (sum(d) / len(d), min(d), len(d)))
