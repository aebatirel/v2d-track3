"""Prepare FlashCHORD-ready floating-hand URDFs for the multi-embodiment showcase (2026-11-06).

For each robot and side: take the source URDF (dex-urdf, or the Dex3 hand subtree of FlashCHORD's G1), keep the
subtree under the chosen root link, rename every link / joint with a "<side>_" prefix and the semantic names that
showcase/floating_hands.py looks for ("<side>_palm" = root, "<side>_<digit>_DP", "<side>_<digit>_fingertip"), add a
fingertip link where the source has none (AUTO: the far end of the distal link's geometry), drop <mimic> tags (coupled
joints are driven independently, a showcase simplification), make mesh paths absolute, and write
OUT/<robot>/<side>.urdf + OUT/<robot>/robot.json (digits, joints, limits) + the FlashCHORD embodiment yaml
OUT/<robot>/emb_<robot>.yaml.
Usage: prep_robots.py DEX_URDF_HANDS_DIR FLASHCHORD_ASSETS_DIR OUT [robot ...]
No robot-specific code outside SPEC.
"""
import json, os, sys, xml.etree.ElementTree as ET

import numpy as np

AUTO = 'AUTO'
# digit name, distal link, fingertip link (or AUTO)
SPEC = {
    'shadow': dict(src='shadow_hand/shadow_hand_{side}_glb.urdf', root='palm', drop=['ee_link', 'imu'],
                   digits=[('thumb', 'thdistal', 'thtip'), ('index', 'ffdistal', 'fftip'), ('middle', 'mfdistal', 'mftip'),
                           ('ring', 'rfdistal', 'rftip'), ('pinky', 'lfdistal', 'lftip')],
                   label='Shadow Hand', fingers=5),
    'allegro': dict(src='allegro_hand/allegro_hand_{side}_glb.urdf', root='base_link', drop=['palm', 'wrist'],
                    digits=[('thumb', 'link_15.0', 'link_15.0_tip'), ('index', 'link_3.0', 'link_3.0_tip'),
                            ('middle', 'link_7.0', 'link_7.0_tip'), ('ring', 'link_11.0', 'link_11.0_tip')],
                    label='Allegro Hand', fingers=4),
    'leap': dict(src='leap_hand/leap_hand_{side}_glb.urdf', root='base', drop=[],
                 digits=[('thumb', 'thumb_fingertip', 'thumb_tip_head'), ('index', 'fingertip', 'index_tip_head'),
                         ('middle', 'fingertip_2', 'middle_tip_head'), ('ring', 'fingertip_3', 'ring_tip_head')],
                 label='LEAP Hand', fingers=4),
    'inspire': dict(src='inspire_hand/inspire_hand_{side}_glb.urdf', root='base', drop=[],
                    digits=[('thumb', 'thumb_distal', 'thumb_tip'), ('index', 'index_intermediate', 'index_tip'),
                            ('middle', 'middle_intermediate', 'middle_tip'), ('ring', 'ring_intermediate', 'ring_tip'),
                            ('pinky', 'pinky_intermediate', 'pinky_tip')],
                    label='Inspire RH56', fingers=5),
    'dex3': dict(src='G1', root='{side}_hand_palm_link', drop=[],
                 digits=[('thumb', '{side}_hand_thumb_2_link', AUTO), ('index', '{side}_hand_index_1_link', AUTO),
                         ('middle', '{side}_hand_middle_1_link', AUTO)],
                 label='Unitree Dex3-1', fingers=3),
    'barrett': dict(src='barrett_hand/bhand_model_glb.urdf', root='base_link', drop=[],
                    digits=[('thumb', 'finger_3_dist_link', AUTO), ('index', 'finger_1_dist_link', AUTO),
                            ('middle', 'finger_2_dist_link', AUTO)],
                    label='Barrett BH8', fingers=3),
    'dclaw': dict(src='dclaw_gripper/dclaw_gripper_glb.urdf', root='base', drop=[],
                  digits=[('thumb', 'link_f1_3', 'link_f1_head'), ('index', 'link_f2_3', 'link_f2_head'),
                          ('middle', 'link_f3_3', 'link_f3_head')],
                  label="D'Claw", fingers=3),
    'panda': dict(src='panda_gripper/panda_gripper_glb.urdf', root='panda_hand', drop=['panda_hand_tcp'],
                  digits=[('thumb', 'panda_leftfinger', AUTO), ('index', 'panda_rightfinger', AUTO)],
                  label='Franka Hand (parallel gripper)', fingers=2,
                  finger_overrides={r'finger_joint\d$': dict(kp=2000.0, kd=40.0, effort_limit=100.0)}),
}
# variants: same robot model, different embodiment settings (written as extra emb_<name>.yaml next to the robot's own)
VARIANTS = {
    # Panda fix (2026-11-06): the pot slid out of the pinch during the flip (phase 1, 0/5). Franka Hand spec: 70 N
    # continuous / 140 N max grip; rubber pads -> torsional friction (condim 4, 1.5 cm patch)
    'panda_pads': dict(robot='panda', finger_overrides={r'finger_joint\d$': dict(kp=5000.0, kd=80.0, effort_limit=140.0)},
                       extra={'pad_condim': 4, 'pad_torsional': 0.015}),
}


def rpy_to_R(rpy):
    r, p, y = rpy
    cr, sr, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])


def vec(s, default='0 0 0'):
    return np.array([float(x) for x in (s or default).split()])


def geom_points(link_el, base_dir):
    """Vertices (link frame) of every collision (else visual) geometry of a link."""
    import trimesh
    pts = []
    els = link_el.findall('collision') or link_el.findall('visual')
    for c in els:
        o = c.find('origin'); xyz = vec(o.get('xyz') if o is not None else None); R = rpy_to_R(vec(o.get('rpy') if o is not None else None))
        g = c.find('geometry')[0]
        if g.tag == 'box':
            h = vec(g.get('size')) / 2
            P = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) * h
        elif g.tag in ('cylinder', 'capsule'):
            r, L = float(g.get('radius')), float(g.get('length'))
            a = np.linspace(0, 2 * np.pi, 16, endpoint=False)
            ring = np.stack([r * np.cos(a), r * np.sin(a), np.zeros_like(a)], 1)
            ext = L / 2 + (r if g.tag == 'capsule' else 0)
            P = np.concatenate([ring + [0, 0, ext], ring - [0, 0, ext]])
        elif g.tag == 'sphere':
            r = float(g.get('radius')); P = np.concatenate([np.eye(3) * r, -np.eye(3) * r])
        elif g.tag == 'mesh':
            fn = g.get('filename'); fn = fn if os.path.isabs(fn) else os.path.join(base_dir, fn)
            m = trimesh.load(fn, force='mesh'); P = np.asarray(m.vertices) * vec(g.get('scale'), '1 1 1')
        else:
            continue
        pts.append(P @ R.T + xyz)
    return np.concatenate(pts) if pts else np.zeros((0, 3))


def auto_tip(link_el, base_dir):
    P = geom_points(link_el, base_dir)
    if not len(P):
        raise ValueError(f"AUTO tip: link {link_el.get('name')} has no geometry")
    far = P[np.argmax(np.linalg.norm(P, axis=1))]; d = far / np.linalg.norm(far)
    proj = P @ d; sel = P[proj >= proj.max() - 0.004]
    return sel.mean(0)


def prep(robot, side, hands_dir, fc_assets, out):
    sp = SPEC[robot]
    if sp['src'] == 'G1':
        src = os.path.join(fc_assets, 'urdfs', 'g1', 'main_with_hand.urdf')
    else:
        src = os.path.join(hands_dir, sp['src'].format(side=side))
    base_dir = os.path.dirname(os.path.abspath(src))
    tree = ET.parse(src); r = tree.getroot()
    links = {l.get('name'): l for l in r.findall('link')}
    joints = r.findall('joint')
    child_of = {j.find('child').get('link'): j for j in joints}
    kids = {}
    for j in joints:
        kids.setdefault(j.find('parent').get('link'), []).append(j.find('child').get('link'))
    root = sp['root'].format(side=side)
    drop = set(sp.get('drop', []))
    keep, stack = [], [root]
    while stack:
        l = stack.pop(); keep.append(l)
        stack += [k for k in kids.get(l, []) if k not in drop]
    keep_set = set(keep)
    digits = [(d, dp.format(side=side), tip if tip == AUTO else tip.format(side=side)) for d, dp, tip in sp['digits']]

    def lname(n):
        if n == root:
            return f'{side}_palm'
        for d, dp, tip in digits:
            if n == dp:
                return f'{side}_{d}_DP'
            if n == tip:
                return f'{side}_{d}_fingertip'
        return n if n.startswith(side + '_') else f'{side}_{n}'

    def jname(n):
        return n if n.startswith(side + '_') else f'{side}_{n}'

    new = ET.Element('robot', name=f'{side}_{robot}')
    for l in keep:
        el = links[l]; el.set('name', lname(l))
        for g in el.iter('mesh'):
            fn = g.get('filename')
            if fn.startswith('package://'):
                fn = fn[len('package://'):]
            if not os.path.isabs(fn):
                fn = os.path.normpath(os.path.join(base_dir, fn))
            if not os.path.exists(fn):
                raise FileNotFoundError(fn)
            g.set('filename', fn)
        if el.find('inertial') is None and l != root:
            ET.SubElement(el, 'inertial').extend([ET.Element('mass', value='0.001'),
                                                  ET.Element('inertia', ixx='1e-7', iyy='1e-7', izz='1e-7', ixy='0', ixz='0', iyz='0')])
        new.append(el)
    jinfo = []
    for l in keep[1:]:
        j = child_of[l]
        j.set('name', jname(j.get('name')))
        j.find('parent').set('link', lname(j.find('parent').get('link')))
        j.find('child').set('link', lname(l))
        m = j.find('mimic')
        if m is not None:
            j.remove(m)
        if j.get('type') in ('revolute', 'prismatic', 'continuous'):
            lim = j.find('limit')
            lo, hi = (float(lim.get('lower', -3.14)), float(lim.get('upper', 3.14))) if lim is not None else (-3.14, 3.14)
            jinfo.append(dict(name=j.get('name'), type=j.get('type'), lower=lo, upper=hi, child=lname(l)))
        new.append(j)
    tips = {}
    for d, dp, tip in digits:
        if tip == AUTO:
            p = auto_tip(links[dp], base_dir)
            tl = ET.SubElement(new, 'link', name=f'{side}_{d}_fingertip')
            ine = ET.SubElement(tl, 'inertial'); ET.SubElement(ine, 'mass', value='0.001')
            ET.SubElement(ine, 'inertia', ixx='1e-7', iyy='1e-7', izz='1e-7', ixy='0', ixz='0', iyz='0')
            tj = ET.SubElement(new, 'joint', name=f'{side}_{d}_tip_fixed', type='fixed')
            ET.SubElement(tj, 'origin', xyz=' '.join(f'{v:.6f}' for v in p), rpy='0 0 0')
            ET.SubElement(tj, 'parent', link=f'{side}_{d}_DP'); ET.SubElement(tj, 'child', link=f'{side}_{d}_fingertip')
            tips[d] = [float(v) for v in p]
        elif tip not in keep_set:
            raise ValueError(f'{robot}: tip link {tip} not in the kept subtree')
    os.makedirs(os.path.join(out, robot), exist_ok=True)
    path = os.path.join(out, robot, f'{side}.urdf')
    ET.indent(new); ET.ElementTree(new).write(path, xml_declaration=True, encoding='utf-8')
    return path, jinfo, tips, [d for d, _, _ in digits]


def emb_yaml(robot, out, digits, name=None, finger_overrides=None, extra=None):
    sp = SPEC[robot]; d = os.path.abspath(os.path.join(out, robot)); name = name or robot
    lines = ['# generated by showcase/prep_robots.py', '_target_: flash_chord.embodiments.floating_hands.FloatingHands', 'config:',
             '  _target_: flash_chord.embodiments.floating_hands.FloatingHandsConfig', f'  robot: {robot}',
             f'  left_urdf_path: {d}/left.urdf', f'  right_urdf_path: {d}/right.urdf', f'  digits: [{", ".join(digits)}]']
    for k, v in (extra or {}).items():
        lines.append(f'  {k}: {v}')
    fo = finger_overrides if finger_overrides is not None else sp.get('finger_overrides')
    if fo:
        lines.append('  finger_overrides:')
        for k, v in fo.items():
            body = ', '.join(f'{a}: {b}' for a, b in v.items())
            lines.append("    '" + k + "': {" + body + "}")
    open(os.path.join(out, robot, f'emb_{name}.yaml'), 'w').write('\n'.join(lines) + '\n')


def main():
    hands_dir, fc_assets, out = sys.argv[1:4]
    robots = sys.argv[4:] or list(SPEC)
    for robot in robots:
        info = dict(robot=robot, label=SPEC[robot]['label'], fingers=SPEC[robot]['fingers'], sides={})
        for side in ('left', 'right'):
            path, jinfo, tips, digits = prep(robot, side, hands_dir, fc_assets, out)
            info['sides'][side] = dict(urdf=path, joints=jinfo, auto_tips=tips)
        info['digits'] = digits
        json.dump(info, open(os.path.join(out, robot, 'robot.json'), 'w'), indent=1)
        emb_yaml(robot, out, digits)
        for vname, v in VARIANTS.items():
            if v['robot'] == robot:
                emb_yaml(robot, out, digits, name=vname, finger_overrides=v.get('finger_overrides'), extra=v.get('extra'))
                print(f'  variant {vname}')
        print(f"{robot}: {len(info['sides']['right']['joints'])} joints per hand, digits {digits}, auto tips {list(info['sides']['right']['auto_tips'])}")


if __name__ == '__main__':
    main()
