"""Task 3: stereo depth error vs distance from the released ego calibration."""
import json
import numpy as np
from common import PUB

cal = json.load(open(f"{PUB}/meta/camera_calibration.json"))
pair = [p for p in cal["stereo_pairs"] if p["camera"] == "ego"][0]
B = pair["baseline_m"]
fl, fr = cal["cameras"][pair["left"]]["fx"], cal["cameras"][pair["right"]]["fx"]
t = np.linalg.norm(np.array(pair["left_to_right"])[:3, 3])
print(f"ego pair left={pair['left']} right={pair['right']} baseline {B*100:.2f} cm (|t| {t*100:.2f} cm); fx L {fl:.1f} R {fr:.1f}; res {cal['cameras'][pair['left']]['resolution']}")
for f, lab in [(min(fl, fr), "full-res f"), (min(fl, fr) / 2, "half-res f (640x400)")]:
    fB = f * B
    print(f"\n{lab}: f={f:.1f} px, f*B={fB:.2f} px*m")
    print(f"{'Z m':>5} {'disp px':>8} {'dZ@0.25px mm':>13} {'dZ@0.5px mm':>12} {'dZ/Z@0.5px %':>13} {'dX@0.25px mm':>13}")
    for Z in np.arange(0.3, 1.01, 0.1):
        d = fB / Z
        dz = lambda e: Z**2 / fB * e
        print(f"{Z:5.1f} {d:8.1f} {dz(0.25)*1e3:13.2f} {dz(0.5)*1e3:12.2f} {dz(0.5)/Z*100:13.2f} {Z/f*0.25*1e3:13.2f}")
a = cal["cameras"]["ego_cam_a"]
print(f"\nego_cam_a (RGB {a['resolution']}, fx {a['fx']:.0f}) offset to stereo-left: {np.linalg.norm(np.array(a['extrinsics_to_stereo_left'])[:3,3])*100:.2f} cm")
print(f"cross-device skew ms: {cal['cross_device_skew_ms']}")
