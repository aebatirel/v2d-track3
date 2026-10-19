#!/usr/bin/env python3
"""Check the R1 implementation of spoon_template.py on the 10 public Track 3 scans (and the URDF inertia formula).

Each published visual GLB is already in the organisers' frame, so re-canonicalising it with R1 should return ~identity:
origin within ~1 mm, same axis order (x smallest, y middle, z largest variance) and the same axis signs. Known exceptions
(note 13 Stage C): the mid-axis (y) skew of blue_cup, mini_dust_pan and white_pot is a near-tie of the "wrong" sign, so the
exact rule flips their (x, y) pair; the organisers' sign step is modelled as noisy there.
Also recomputes each URDF <inertial> as 0.3 kg x uniform triangle-surface inertia of the collision (or single) mesh.
Outputs: prints a table, writes public_frame_check.json next to this file. Ground truth poses are not used.
"""
import json
import os
import re
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spoon_template as st  # noqa: E402

PUB = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public"
OBJS = ["beige_cup", "blue_cup", "mini_dust_pan", "mini_sweeper", "plastic_dish_rack", "water_pitcher", "white_pot",
        "white_pot_lid", "wooden_piece_1", "wooden_piece_2"]


def load(path):
    m = trimesh.load(path, force="mesh", process=False)
    return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


def urdf_inertial(name):
    txt = open(os.path.join(PUB, "urdf", f"{name}_rigid.urdf")).read()
    blk = txt[txt.index("<inertial>"): txt.index("</inertial>")]
    org = [float(x) for x in re.search(r'<origin xyz="([^"]+)"', blk).group(1).split()]
    I = {k: float(v) for k, v in re.findall(r'(i[xyz]{2})="([^"]+)"', blk)}
    col = re.search(r'<collision>.*?filename="([^"]+)"', txt, re.S).group(1)
    return np.array(org), np.array([[I["ixx"], I["ixy"], I["ixz"]], [I["ixy"], I["iyy"], I["iyz"]], [I["ixz"], I["iyz"], I["izz"]]]), col


def main():
    rows = []
    for name in OBJS:
        d = os.path.join(PUB, "mesh", name)
        vis = os.path.join(d, f"{name}_visual.glb") if os.path.exists(os.path.join(d, f"{name}_visual.glb")) else os.path.join(d, f"{name}.glb")
        V, F = load(vis)
        rec = dict(object=name, mesh=os.path.basename(vis), faces=int(len(F)))
        for rule in ("mid", "x"):
            R, c, w, sk = st.r1_frame(V, F, rule)
            diag = np.array([R[i, i] for i in range(3)])
            order_ok = all(int(np.argmax(np.abs(R[i]))) == i for i in range(3))
            ang = np.degrees(np.arccos(np.clip(np.abs(diag), 0, 1)))
            rec[rule] = dict(origin_mm=float(np.linalg.norm(c) * 1e3), axis_order_kept=bool(order_ok),
                             signs=np.sign(diag).astype(int).tolist(), identity=bool(order_ok and (diag > 0).all()),
                             max_axis_angle_deg=float(ang.max()))
        # skews along the PUBLISHED axes (identity) about the surface centroid
        c, C, _ = st.surface_moments(V, F)
        rec["published_axis_skews"] = [round(st.skew_along(V, F, c, np.eye(3)[i]), 5) for i in range(3)]
        rec["sd_mm"] = (np.sqrt(np.linalg.eigvalsh(C)) * 1e3).round(2).tolist()
        # URDF inertia check (uniform triangle-surface estimate, 0.3 kg, about the collision-mesh surface centroid)
        org, I_urdf, colpath = urdf_inertial(name)
        Vc, Fc = load(os.path.normpath(os.path.join(PUB, "urdf", colpath)))
        cc, I = st.surface_inertia(Vc, Fc, 0.3)
        rec["urdf_inertia_rel_err"] = float(np.abs(I - I_urdf).max() / np.abs(I_urdf).max())
        rec["urdf_origin_err_mm"] = float(np.linalg.norm(cc - org) * 1e3)
        rows.append(rec)
        m = rec["mid"]
        print(f"{name:18s} origin {m['origin_mm']:.2e} mm  order_ok {m['axis_order_kept']}  signs(mid) {m['signs']}  "
              f"identity(mid) {m['identity']}  identity(x-rule) {rec['x']['identity']}  max axis angle {m['max_axis_angle_deg']:.2e} deg  "
              f"skews(pub) {rec['published_axis_skews']}  urdf I rel.err {rec['urdf_inertia_rel_err']:.1e}", flush=True)
    summ = dict(
        n=len(rows),
        origin_max_mm=max(r["mid"]["origin_mm"] for r in rows),
        axis_order_kept=sum(r["mid"]["axis_order_kept"] for r in rows),
        identity_mid_rule=sum(r["mid"]["identity"] for r in rows),
        exceptions_mid_rule=[dict(object=r["object"], signs=r["mid"]["signs"], skew_y_published=r["published_axis_skews"][1])
                             for r in rows if not r["mid"]["identity"]],
        identity_x_rule=sum(r["x"]["identity"] for r in rows),
        exceptions_x_rule=[dict(object=r["object"], signs=r["x"]["signs"], skew_x_published=r["published_axis_skews"][0])
                           for r in rows if not r["x"]["identity"]],
        z_sign_kept=sum(r["mid"]["signs"][2] == 1 for r in rows),
        urdf_inertia_max_rel_err=max(r["urdf_inertia_rel_err"] for r in rows),
        urdf_origin_max_err_mm=max(r["urdf_origin_err_mm"] for r in rows),
    )
    print(json.dumps(summ, indent=1))
    with open(os.path.join(HERE, "public_frame_check.json"), "w") as f:
        json.dump(dict(summary=summ, rows=rows), f, indent=1)


if __name__ == "__main__":
    main()
