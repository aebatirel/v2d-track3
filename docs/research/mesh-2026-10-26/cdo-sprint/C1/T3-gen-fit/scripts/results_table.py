"""Make the RESULTS.md tables from gates.json and build_manifest.json (no new numbers)."""
import json, sys
g = json.load(open(sys.argv[1])); b = {r['object']: r for r in json.load(open(sys.argv[2]))}
print('| Object | Raw pick [D] CD-O / add_med / flips | Fitted [D] CD-O / add_med / flips (extra) | d vs raw | Gate baseline(s) | CD-O ok | ADD ok | flips ok | WIN | vs C0 | GT-free held-out tmean90 mm in -> fit |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for r in g['rows']:
    o = r['object']; m = b.get(o, {})
    if 'cdo' not in r:
        print(f"| {o} | {r['raw_cdo']:.4f} / {r['raw_add_med']:.2f} / {r['raw_flips']} of {r['raw_n']} | ERROR {r.get('error')} | | | | | | | | |"); continue
    fx = f" ({r['flips_extra']}/{r['n_extra']} extra)" if r.get('n_extra') and r['n_extra'] >= 30 else ''
    bl = '; '.join(f"{p['pair']} {p['base_cdo']:.4f} / {p['base_add_med']:.2f}" for p in r['pairs'])
    ck = '/'.join('y' if p['cdo_ok'] else 'n' for p in r['pairs'])
    ak = '/'.join('y' if p['add_ok'] else 'n' for p in r['pairs'])
    fk = 'y' if r['pairs'][0]['flip_ok'] else 'n'
    c0 = '' if 'c0_cdo' not in r else (f"C0 {r['c0_cdo']:.4f}: " + ('beats' if r['beats_c0_by_0.02'] else 'no'))
    print(f"| {o} | {r['raw_cdo']:.4f} / {r['raw_add_med']:.2f} / {r['raw_flips']} of {r['raw_n']} | {r['cdo']:.4f} / {r['add_med']:.2f} / "
          f"{r['flips_all']} of {r['n_seeds']}{fx} | {r['d_vs_raw']:+.4f} | {bl} | {ck} | {ak} | {fk} | {'**WIN**' if r['win'] else 'no'} | {c0} | "
          f"{m.get('held_tmean90_in', float('nan')):.2f} -> {m.get('held_tmean90_fit', float('nan')):.2f} |")
print(f"\nWINs {g['wins']} of 10; fitted worse than raw on {g['worse_than_raw']} of {g['n_scored']}; H-GF: {g['verdict']}")
