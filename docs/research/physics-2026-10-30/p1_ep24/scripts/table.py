"""Print a compact table of settle_p1.py results. Usage: table.py RUN_JSON..."""
import json, sys, os
print('run | host drift cm / tilt deg | guest drift cm / tilt deg | rel sink mm | rel change cm/deg | NaN | guest on table | guest below host low | low start h/g mm | crit (hd,gd,ht,gt,sink,nan)')
for f in sys.argv[1:]:
    d = json.load(open(f)); s = d['summary']; c = d['criteria_excl_fallthrough']
    h, g = s['host'], s['guest']
    print(f"{os.path.basename(f)[:-5]:26s} | {h['drift_cm']:.3f} / {h['tilt_deg']:.2f} | {g['drift_cm']:.3f} / {g['tilt_deg']:.2f} | {s['rel_sink_mm']:+.2f} | "
          f"{s['rel_change_cm']:.3f}/{s['rel_change_deg']:.2f} | {s['nan']} | {s['guest_on_table_end']}/{s['copies']} | {s['guest_below_host_lowest_end']}/{s['copies']} | "
          f"{h['low_start_mm']:.1f}/{g['low_start_mm']:.1f} | {''.join('P' if c[k] else 'F' for k in ('host_drift','guest_drift','host_tilt','guest_tilt','rel_sink','no_nan'))}")
