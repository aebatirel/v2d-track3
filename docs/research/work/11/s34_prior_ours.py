"""Stage C retry: slot-0 anchor (and key co-object) yaw priors expressed in OUR frame-0 frame, y_ours = y_m - W_e,
using the as-given-K (native) W table (s27_stats_native_best4.json) and the flipped table for comparison.
Our frame: z up (own table normal), x = frame-0 optical axis projected on the table, y = z cross x (image-left).
Yaw = heading of the c11.HREF body axis. 'sym' = 2 for two-fold objects: vision gives yaw mod 180, the full-circle prior picks the branch. Priors from s13 (section 4)."""
import json
Wn = json.load(open("s27_stats_native_best4.json")); Wf = json.load(open("s27_stats_flipped_best4.json"))
w = lambda a: (a + 180) % 360 - 180
P = [(10, "blue_cup", 41.1, 360, "Cup_Stack n=1"), (14, "blue_cup", 64.1, 360, "twin diff 2.7 (rel-to-rack preferred)"),
     (14, "plastic_dish_rack", 89.5, 180, "branch"), (15, "plastic_dish_rack", 91.0, 180, "cross-task rms 1.4"),
     (16, "plastic_dish_rack", 91.0, 180, "cross-task rms 1.4"), (19, "mini_sweeper", 16.3, 180, "ep 18 n=1"),
     (20, "blue_cup", -68.8, 360, "twin diff 8.0; cup in hand at f0"), (25, "wooden_piece_1", -177.2, 180, "rms 1.5"),
     (28, "plastic_dish_rack", 92.3, 180, "rms 0.7"), (30, "mini_sweeper", -3.5, 180, "ep 31 n=1")]
out = []
print("ev  object              y_mocap  W_native  y_ours(native)  y_ours(flipped)  mod  note")
for ev, ob, ym, mod, note in P:
    wn = Wn[f"e{ev}"]["pred_median"]; wf = Wf[f"e{ev}"]["pred_median"]
    yn = w(ym - wn); yf = w(ym - wf)
    # two-fold: keep the full-circle value; vision measures yaw mod 180 and the prior picks the nearest branch
    out.append(dict(ev=ev, obj=ob, y_mocap=ym, W_native=round(wn, 2), y_ours_native=round(yn, 1), y_ours_flipped=round(yf, 1), mod=mod, note=note))
    print(f"{ev:2d}  {ob:18s} {ym:8.1f}  {wn:8.2f}  {yn:12.1f}  {yf:14.1f}  {mod:4d}  {note}")
json.dump(out, open("s34_prior_ours.json", "w"), indent=1)
