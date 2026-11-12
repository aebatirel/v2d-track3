"""Synthetic tests of pipeline/ds_modulate.py (2026-11-13, phase 1 of docs/research/work/ds-modulation-20261113/PREREG.md).
No episode data is read: every geometry, path and reference here is made up. Run with pytest, or as a script (needs numpy,
scipy, trimesh, pyarrow)."""
import importlib.util, json, os, sys, tempfile

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
spec = importlib.util.spec_from_file_location('ds_modulate', os.path.join(REPO, 'pipeline', 'ds_modulate.py'))
ds = importlib.util.module_from_spec(spec); spec.loader.exec_module(ds)
P = dict(ds.DEFAULTS)
FPS = 20.0


# ----------------------------------------------------------------------------- helpers
def sphere_surface(radius, spacing=0.003, name='ball'):
    import trimesh
    m = trimesh.creation.icosphere(subdivisions=5, radius=radius)
    return ds.SampledSurface.from_mesh(m.vertices, m.faces, spacing, name)


def static(surf, center, T):
    pos = np.tile(np.asarray(center, float), (T, 1)); rot = np.tile(np.eye(3), (T, 1, 1))
    return ds.PosedObstacle(surf, pos, rot, np.zeros((T, 3)))


def line(p0, p1, T):
    s = np.linspace(0, 1, T)[:, None]
    return (1 - s) * np.asarray(p0, float) + s * np.asarray(p1, float)


def run_point(p, obstacles, body=None, prm=P):
    """Modulate the whole path p (one window) for a body of offsets BODY (default: a single point)."""
    offs = np.zeros((1, 3)) if body is None else np.asarray(body, float)
    return ds.modulate_window(p, 0, len(p) - 1, FPS, lambda tf: [(offs, 'hand')],
                              lambda tf: [(o, ('hand',)) for o in obstacles], prm)


def sphere_dist(x, c, r):
    return np.linalg.norm(np.asarray(x) - np.asarray(c), axis=-1) - r


# ----------------------------------------------------------------------------- the modulation itself
def test_eigenvalues_of_modulation_matrix():
    n = np.array([0.3, -0.2, 0.9]); n /= np.linalg.norm(n); a = 0.4
    v_in = -n                                                   # approaching: KZB eigenvalues
    M = ds.modulation_matrix(n, a, v_in, P)
    E = ds.tangent_basis(n)
    assert np.allclose(M @ n, (1 - a) * n)
    assert np.allclose(M @ E[:, 1], (1 + a) * E[:, 1]) and np.allclose(M @ E[:, 2], (1 + a) * E[:, 2])
    assert np.allclose(M, M.T)                                  # E orthonormal: E D E^T is symmetric


def test_boundary_blocks_normal_velocity_and_far_is_identity():
    n = np.array([0, 0, 1.0]); f = np.array([0.2, 0.0, -0.3])   # moving into the surface
    v = ds.modulate(f, [(n, 1.0, np.zeros(3))], P)              # u = 1/Gamma = 1: on the inflated boundary
    assert abs(v @ n) < 1e-12 and v[0] > f[0]                   # normal part removed, tangent stretched (x2)
    assert np.allclose(ds.modulate(f, [], P), f)
    assert np.allclose(ds.modulate(f, [(n, 0.0, np.zeros(3))], P), f)


def test_tail_negligence_is_continuous_and_identity_when_leaving_straight_out():
    n = np.array([0, 0, 1.0])
    for u in (0.3, 1.0):
        out = ds.modulate(np.array([0.0, 0.0, 0.5]), [(n, u, np.zeros(3))], P)
        assert np.allclose(out, [0, 0, 0.5])                    # leaving along the normal: M = I
        lo = ds.modulate(np.array([0.3, 0.0, -1e-7]), [(n, u, np.zeros(3))], P)
        hi = ds.modulate(np.array([0.3, 0.0, +1e-7]), [(n, u, np.zeros(3))], P)
        assert np.linalg.norm(lo - hi) < 1e-5                   # no jump across the tangent plane


def test_inv_gamma_profile():
    m, d_inf, R = P['margin'], P['d_inf'], 0.05
    assert abs(float(ds.inv_gamma(m, R, m, d_inf)) - 1) < 1e-12
    assert float(ds.inv_gamma(d_inf, R, m, d_inf)) == 0.0 and float(ds.inv_gamma(0.5, R, m, d_inf)) == 0.0
    d = np.linspace(m, d_inf, 50); u = ds.inv_gamma(d, R, m, d_inf)
    assert np.all(np.diff(u) < 0)                               # monotone
    assert float(ds.inv_gamma(0.0, R, m, d_inf)) > 1            # inside the margin: Gamma < 1


def test_kzb_weights():
    w = ds.kzb_weights(np.array([0.5, 0.25]))                   # Gamma 2 and 4
    assert np.allclose(w, [3 / 4, 1 / 4]) and abs(w.sum() - 1) < 1e-12
    assert np.allclose(ds.kzb_weights(np.array([1.0, 0.5])), [1, 0])   # touching one obstacle: only it acts
    assert np.allclose(ds.kzb_weights(np.array([0.7])), [1])


# ----------------------------------------------------------------------------- signed distance
def test_sampled_sphere_signed_distance():
    r = 0.05; s = sphere_surface(r)
    rng = np.random.default_rng(1); q = rng.uniform(-0.12, 0.12, (2000, 3))
    d, g = s.query(q); true = np.linalg.norm(q, axis=1) - r
    near = np.abs(true) < 0.03
    assert np.abs(d - true).max() < 0.003                       # within the sample spacing
    assert (np.sign(d[np.abs(true) > 0.003]) == np.sign(true[np.abs(true) > 0.003])).all()
    radial = q / np.linalg.norm(q, axis=1, keepdims=True)
    assert np.einsum('ij,ij->i', g[near], radial[near]).min() > 0.9


def test_convex_pieces_union():
    box = lambda lo, hi: np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])], float)
    s = ds.SampledSurface.from_convex_pieces([box((0, 0, 0), (0.1, 0.04, 0.04)), box((0.06, 0, 0), (0.1, 0.04, 0.12))], 0.003)
    inside = np.array([[0.08, 0.02, 0.02], [0.08, 0.02, 0.10], [0.02, 0.02, 0.02]])
    outside = np.array([[0.03, 0.02, 0.08], [0.2, 0.02, 0.02], [0.05, -0.05, 0.02]])
    assert (s.query(inside)[0] < 0).all() and (s.query(outside)[0] > 0).all()
    d, _ = s.query(np.array([[0.03, 0.02, 0.08]]))              # 3 cm above the low box, 3 cm left of the tall one
    assert abs(d[0] - 0.03) < 0.004
    # no sample of one piece lies strictly inside the other (union boundary only)
    assert not ((s.P[:, 0] > 0.062) & (s.P[:, 0] < 0.098) & (s.P[:, 2] > 0.002) & (s.P[:, 2] < 0.038)
                & (s.P[:, 1] > 0.002) & (s.P[:, 1] < 0.038)).any()


# ----------------------------------------------------------------------------- a path past a sphere
def test_sphere_on_straight_path_avoided_goal_and_timing_kept():
    T, r, c = 41, 0.05, np.array([0.0, 0.0, 0.0])
    p = line([-0.25, 0.01, 0.0], [0.25, 0.01, 0.0], T)          # 1 cm off the centre line, through the ball
    X, info = run_point(p, [static(sphere_surface(r), c, T)])
    assert X.shape == p.shape                                   # same frames: timing kept
    assert np.array_equal(X[0], p[0]) and np.array_equal(X[-1], p[-1])   # start and goal exactly
    d_orig = sphere_dist(p, c, r).min(); d_mod = sphere_dist(X, c, r)
    assert d_orig < -0.039                                      # the original passes 4 cm deep
    L = P['fade']
    assert d_mod[:-L].min() > 0.75 * P['margin'], d_mod.min()   # outside the margin up to the fade
    assert d_mod.min() > 0                                      # and never inside the ball
    assert info['max_dev_m'] < r + P['margin'] + 0.02           # bounded detour
    step = np.linalg.norm(p[1] - p[0])                          # 1.25 cm per frame
    # per-frame travel <= lambda_t,max x (reference step + K x deviation x dt): the tracking DS's own speed bound
    bound = P['lam_t_max'] * (step + P['k_track'] * info['max_dev_m'] / FPS) + 1e-3
    assert np.linalg.norm(np.diff(X, axis=0), axis=1).max() < bound
    assert np.linalg.norm(np.diff(X, 2, axis=0), axis=1).max() < 2 * step   # velocity changes by less than 2 steps
    assert not info['stalled']


def test_no_change_far_from_obstacles():
    T = 41; ball = static(sphere_surface(0.05), [0, 0, 0], T)
    p = line([-0.25, 0.05 + P['d_inf'] + 0.02, 0.0], [0.25, 0.05 + P['d_inf'] + 0.02, 0.0], T)
    X, info = run_point(p, [ball])
    assert np.abs(X - p).max() < 1e-12 and info['active_substeps'] == 0
    wavy = p + np.c_[np.zeros(T), 0.01 * np.sin(np.linspace(0, 6, T)), 0.02 * np.cos(np.linspace(0, 4, T))]
    X2, _ = run_point(wavy, [ball])
    assert np.abs(X2 - wavy).max() < 1e-12                      # also for a curved path


def test_grazing_path_outside_margin_unchanged_inside_influence_bent_little():
    T = 41; ball = static(sphere_surface(0.05), [0, 0, 0], T)
    p = line([-0.25, 0.05 + 0.03, 0.0], [0.25, 0.05 + 0.03, 0.0], T)    # passes 3 cm from the surface
    X, info = run_point(p, [ball])
    assert info['active_substeps'] > 0
    assert sphere_dist(X, [0, 0, 0], 0.05).min() > 0.025         # stays clear
    assert np.linalg.norm(X - p, axis=1).max() < 0.01            # and is moved by less than 1 cm


def test_exact_centre_line_is_a_saddle_guard_leaves_window_unchanged():
    """KZB: the modulated field has saddle points on the obstacle boundary. Head-on along the centre line the point stops
    at the margin while the reference goes on; fading back would snap it through the ball, so the stall guard leaves the
    window unchanged and reports it (a known limitation that phase 2 counts)."""
    T, r = 41, 0.05
    p = line([-0.25, 0.0, 0.0], [0.25, 0.0, 0.0], T)
    X, info = run_point(p, [static(sphere_surface(r), [0, 0, 0], T)])
    assert info['stalled'] and info['fade_pull_m'] > 0.1
    assert np.array_equal(X, p)


def test_extended_body_cspace():
    """A two-point body (wrist and a point 6 cm to the side): the side point's line crosses the ball while the wrist's
    passes 3 cm from it; the side point, not the wrist, must clear the ball."""
    T, r = 41, 0.04
    body = np.array([[0, 0, 0], [0, 0.06, 0]])
    p = line([-0.25, -0.07, 0.0], [0.25, -0.07, 0.0], T)          # side point at y = -0.01: 3 cm deep
    X, info = run_point(p, [static(sphere_surface(r), [0, 0, 0], T)], body=body)
    assert sphere_dist(p + body[1], [0, 0, 0], r).min() < -0.02
    assert sphere_dist((X + body[1])[:-P['fade']], [0, 0, 0], r).min() > 0.75 * P['margin']
    assert sphere_dist(X, [0, 0, 0], r).min() > 0.75 * P['margin'] and not info['stalled']


def test_concave_cspace_obstacle_documented_limitation():
    """The same body straddling the ball (wrist 5 cm on one side, side point 1 cm on the other): the C-space obstacle is
    two overlapping balls (a concave waist). KZB's guarantee needs convex / star-shaped obstacles; here the body enters
    the margin. Recorded as a limitation, not hidden."""
    T, r = 41, 0.04
    body = np.array([[0, 0, 0], [0, 0.06, 0]])
    p = line([-0.25, -0.05, 0.0], [0.25, -0.05, 0.0], T)
    X, info = run_point(p, [static(sphere_surface(r), [0, 0, 0], T)], body=body)
    worst = min(sphere_dist(X, [0, 0, 0], r).min(), sphere_dist(X + body[1], [0, 0, 0], r).min())
    assert worst < P['margin'] or info['stalled']                 # the guarantee does not hold here


def test_moving_obstacle_pushes_a_resting_point():
    T, r = 41, 0.04
    p = np.tile([0.0, 0.01, 0.0], (T, 1))                         # the reference stands still
    pos = line([-0.2, 0, 0], [0.2, 0, 0], T); vel = np.tile((pos[1] - pos[0]) * FPS, (T, 1))
    ball = ds.PosedObstacle(sphere_surface(r), pos, np.tile(np.eye(3), (T, 1, 1)), vel)
    X, _ = run_point(p, [ball])
    d = sphere_dist(X, pos, r)
    assert sphere_dist(p, pos, r).min() < -0.02 and d[:-P['fade']].min() > 0.5 * P['margin'], d.min()


def test_two_obstacles_gap():
    T, r = 61, 0.04
    p = line([-0.3, 0.0, 0.0], [0.3, 0.0, 0.0], T)
    a = static(sphere_surface(r, name='a'), [0, 0.065, 0], T); b = static(sphere_surface(r, name='b'), [0, -0.065, 0], T)
    X, _ = run_point(p, [a, b])                                   # the line runs through a 5 cm gap: 2.5 cm each side
    assert min(sphere_dist(X, [0, 0.065, 0], r).min(), sphere_dist(X, [0, -0.065, 0], r).min()) > 0.75 * P['margin']
    assert np.linalg.norm((X - p)[:, 1:], axis=1).max() < 0.005    # not pushed sideways in a symmetric gap
    assert np.abs((X - p)[:, 0]).max() < 0.02                       # tangential stretch: at most 2 cm along the path


# ----------------------------------------------------------------------------- reference I/O, end to end (synthetic)
def _synthetic_reference(tmp, ball_y=0.045):
    """A made-up 60-frame reference: the right hand (a 4 x 4 x 2 cm palm) reaches along x for a box at x = +0.10 past a
    ball (r 4 cm) BALL_Y off its straight line (0.045: the palm cuts 1.5 cm into it), grasps the box at f40 (MANO
    contacts) and lifts it 15 cm from f44; the left hand parks far away."""
    import pyarrow as pa, pyarrow.parquet as pq, trimesh
    T, B = 60, 2
    os.makedirs(f'{tmp}/meshes', exist_ok=True); os.makedirs(f'{tmp}/urdf', exist_ok=True)
    trimesh.creation.icosphere(subdivisions=4, radius=0.04).export(f'{tmp}/meshes/ball.glb')
    trimesh.creation.box((0.06, 0.06, 0.06)).export(f'{tmp}/meshes/box.glb')
    trimesh.creation.box((0.04, 0.04, 0.02)).export(f'{tmp}/urdf/palm.stl')
    for s in ('left', 'right'):
        open(f'{tmp}/urdf/{s}_sharpawave.urdf', 'w').write(
            f'<robot name="h"><link name="{s}_hand_C_MC"><collision><origin xyz="0 0 0" rpy="0 0 0"/>'
            f'<geometry><mesh filename="palm.stl"/></geometry></collision></link></robot>')
    os.makedirs(f'{tmp}/ref/reconstructed_stage', exist_ok=True); os.makedirs(f'{tmp}/ref/processed/s/r', exist_ok=True)
    open(f'{tmp}/ref/reconstructed_stage/x_support.usda', 'w').write(
        'def Cylinder "table" ( )\n{\n double height = 0.020000\n double radius = 0.450000\n'
        ' double3 xformOp:translate = (0, 0, 0.590000)\n}\n')
    z = 0.60 + 0.03
    box = np.tile([0.10, 0.0, z], (T, 1)); box[44:, 2] += np.minimum(np.arange(T - 44), 10) * 0.015
    ball = np.tile([-0.12, ball_y, 0.64], (T, 1))
    OP = np.stack([ball, box], 1); OQ = np.tile([1.0, 0, 0, 0], (T, B, 1))
    wr = np.zeros((T, 3)); wr[:41] = line([-0.40, 0.0, z], [0.10 - 0.05, 0.0, z], 41)
    wr[41:] = wr[40]; wr[44:, 2] += np.minimum(np.arange(T - 44), 10) * 0.015
    wl = np.tile([-0.2, 0.40, 0.75], (T, 1))
    cols = dict(fps=FPS, object_body_names=['ball', 'box'], object_body_position=OP.tolist(),
                object_body_wxyz=OQ.tolist(), object_root_position=OP[:, 0].tolist())
    K = 16
    for s, w in (('left', wl), ('right', wr)):
        fr = np.zeros((T, 1, 7)); fr[:, 0, :3] = w; fr[:, 0, 3] = 1.0
        cols[f'robot_{s}_wrist_position'] = w.tolist(); cols[f'robot_{s}_frames'] = fr.tolist()
        cols[f'{s}_robot_frame_names'] = [f'{s}_hand_C_MC']
        cp = np.zeros((T, K, 3)); cn = np.zeros((T, K, 3)); pid = np.zeros((T, K), int)
        if s == 'right':
            cn[40:, :3] = [1.0, 0, 0]; pid[40:, :3] = 2; cp[40:, :3] = box[40:, None, :] - [0.03, 0, 0]
        cols[f'mano_{s}_object_contact_positions'] = cp.tolist(); cols[f'mano_{s}_object_contact_normals'] = cn.tolist()
        cols[f'mano_{s}_object_contact_part_ids'] = pid.tolist(); cols[f'mano_{s}_link_contact_positions'] = cp.tolist()
    path = f'{tmp}/ref/processed/s/r/ref.parquet'
    pq.write_table(pa.table({k: [v] for k, v in cols.items()}), path)
    return path, OP


def test_end_to_end_synthetic_reference():
    import pyarrow.parquet as pq
    with tempfile.TemporaryDirectory() as tmp:
        path, OP = _synthetic_reference(tmp)
        t = pq.read_table(path)
        new, rep, lab = ds.modulate_reference(t, path, f'{tmp}/meshes', f'{tmp}/urdf',
                                              f'{tmp}/ref/reconstructed_stage/x_support.usda', P, geom='mesh')
        T = 60
        w0 = ds.col(t, 'robot_right_wrist_position').reshape(T, 3); w1 = ds.col(new, 'robot_right_wrist_position').reshape(T, 3)
        f1 = ds.col(new, 'robot_right_frames').reshape(T, 1, 7)
        role = lab['right']['role']
        assert role[0] == 'A' and (role[40:44] == '-').all()          # approach window, then grasp / lift-off zone
        assert np.allclose(f1[:, 0, :3], w1)                          # frames moved with the wrist
        assert np.array_equal(w0[role == '-'], w1[role == '-'])        # grasp zone untouched
        assert np.array_equal(ds.col(t, 'robot_left_wrist_position'), ds.col(new, 'robot_left_wrist_position'))
        # the palm (4 x 4 x 2 cm) clears the ball in the modulated approach; the original went through it
        palm_r = np.linalg.norm([0.02, 0.02, 0.01])
        hand = ds.hand_world(f1, ds.load_hand_samples(f'{tmp}/urdf', 'right', ['right_hand_C_MC'], P['body_spacing']))
        surf = ds.object_surface('ball', f'{tmp}/meshes', 'mesh', P['obs_spacing'])
        dpalm = np.array([surf.query(hand[i] - OP[i, 0])[0].min() for i in range(T)])
        win = np.nonzero(role == 'A')[0]; last = max(b for a, b in ds.runs(role == 'A') if a == 0)
        inside = [i for i in win if i <= last - P['fade']]
        hand0 = ds.hand_world(ds.col(t, 'robot_right_frames').reshape(T, 1, 7),
                              ds.load_hand_samples(f'{tmp}/urdf', 'right', ['right_hand_C_MC'], P['body_spacing']))
        dpalm0 = np.array([surf.query(hand0[i] - OP[i, 0])[0].min() for i in range(T)])
        assert dpalm0.min() < -0.01                                   # the original palm cuts into the ball
        assert dpalm[inside].min() > 0.5 * P['margin'], dpalm[inside].min()
        assert not any(w['stalled'] for w in rep['hands']['right'])
        # window ends exactly on the original (pre-grasp kept)
        assert np.array_equal(w0[last], w1[last])
        # objects untouched (no transport frame: the box never gets 8 cm clear of the table in this scene) or moved
        # exactly with the hand in transport frames
        OP1 = ds.col(new, 'object_body_position').reshape(T, 2, 3)
        X = role == 'X'
        assert np.allclose(OP1[~X], OP[~X])
        if X.any():
            assert np.allclose(OP1[X, 1] - OP[X, 1], (w1 - w0)[X])
        json.dumps(rep)                                               # the report is JSON-serialisable


def _carry_reference(tmp):
    """A made-up 90-frame carry: the right hand holds a 6 cm box from f0 (MANO contacts), lifts it 15 cm over f4-13 and
    carries it 45 cm along +y over f14-89 past a ball (r 4 cm) whose surface the box's side cuts by 1.5 cm; the palm is
    5 cm behind the box and never near the ball."""
    import pyarrow as pa, pyarrow.parquet as pq, trimesh
    T, B, z = 90, 2, 0.63
    _scene_files(tmp)
    box = np.tile([0.10, 0.0, z], (T, 1)); box[4:14, 2] += np.linspace(0.015, 0.15, 10); box[14:, 2] = z + 0.15
    box[14:, 1] = np.linspace(0, 0.45, T - 14)
    ball = np.tile([0.10 + 0.055, 0.20, z + 0.15], (T, 1))
    OP = np.stack([ball, box], 1)
    wr = box - [0.05, 0.0, 0.0]; wl = np.tile([-0.2, 0.40, 0.75], (T, 1))
    contacts = np.zeros(T, bool); contacts[:] = True
    return _write_reference(tmp, T, OP, wr, wl, contacts), OP


def _scene_files(tmp):
    import trimesh
    os.makedirs(f'{tmp}/meshes', exist_ok=True); os.makedirs(f'{tmp}/urdf', exist_ok=True)
    trimesh.creation.icosphere(subdivisions=4, radius=0.04).export(f'{tmp}/meshes/ball.glb')
    trimesh.creation.box((0.06, 0.06, 0.06)).export(f'{tmp}/meshes/box.glb')
    trimesh.creation.box((0.04, 0.04, 0.02)).export(f'{tmp}/urdf/palm.stl')
    for s in ('left', 'right'):
        open(f'{tmp}/urdf/{s}_sharpawave.urdf', 'w').write(
            f'<robot name="h"><link name="{s}_hand_C_MC"><collision><origin xyz="0 0 0" rpy="0 0 0"/>'
            f'<geometry><mesh filename="palm.stl"/></geometry></collision></link></robot>')
    os.makedirs(f'{tmp}/ref/reconstructed_stage', exist_ok=True); os.makedirs(f'{tmp}/ref/processed/s/r', exist_ok=True)
    open(f'{tmp}/ref/reconstructed_stage/x_support.usda', 'w').write(
        'def Cylinder "table" ( )\n{\n double height = 0.020000\n double radius = 0.450000\n'
        ' double3 xformOp:translate = (0, 0, 0.590000)\n}\n')


def _write_reference(tmp, T, OP, wr, wl, right_contacts):
    import pyarrow as pa, pyarrow.parquet as pq
    B = OP.shape[1]; K = 16
    cols = dict(fps=FPS, object_body_names=['ball', 'box'], object_body_position=OP.tolist(),
                object_body_wxyz=np.tile([1.0, 0, 0, 0], (T, B, 1)).tolist(), object_root_position=OP[:, 0].tolist())
    for s, w in (('left', wl), ('right', wr)):
        fr = np.zeros((T, 1, 7)); fr[:, 0, :3] = w; fr[:, 0, 3] = 1.0
        cols[f'robot_{s}_wrist_position'] = w.tolist(); cols[f'robot_{s}_frames'] = fr.tolist()
        cols[f'{s}_robot_frame_names'] = [f'{s}_hand_C_MC']
        cp = np.zeros((T, K, 3)); cn = np.zeros((T, K, 3)); pid = np.zeros((T, K), int)
        if s == 'right':
            on = np.asarray(right_contacts, bool)
            cn[on, :3] = [1.0, 0, 0]; pid[on, :3] = 2; cp[on, :3] = OP[on, 1, None, :] - [0.03, 0, 0]
        cols[f'mano_{s}_object_contact_positions'] = cp.tolist(); cols[f'mano_{s}_object_contact_normals'] = cn.tolist()
        cols[f'mano_{s}_object_contact_part_ids'] = pid.tolist(); cols[f'mano_{s}_link_contact_positions'] = cp.tolist()
    path = f'{tmp}/ref/processed/s/r/ref.parquet'
    pq.write_table(pa.table({k: [v] for k, v in cols.items()}), path)
    return path


def test_end_to_end_transport_held_object_clears_bystander():
    import pyarrow.parquet as pq
    with tempfile.TemporaryDirectory() as tmp:
        path, OP = _carry_reference(tmp)
        t = pq.read_table(path); T = len(OP)
        new, rep, lab = ds.modulate_reference(t, path, f'{tmp}/meshes', f'{tmp}/urdf',
                                              f'{tmp}/ref/reconstructed_stage/x_support.usda', P, geom='mesh')
        role = lab['right']['role']
        assert role[0] == '-' and 'X' in role                        # lift-off zone, then a transport window
        w0 = ds.col(t, 'robot_right_wrist_position').reshape(T, 3); w1 = ds.col(new, 'robot_right_wrist_position').reshape(T, 3)
        OP1 = ds.col(new, 'object_body_position').reshape(T, 2, 3)
        assert np.allclose(OP1[:, 1] - OP[:, 1], w1 - w0)            # the held box moved exactly with the wrist
        assert np.allclose(OP1[:, 0], OP[:, 0])                      # the bystander did not move
        C0 = ds.col(t, 'mano_right_object_contact_positions').reshape(T, -1, 3)
        C1 = ds.col(new, 'mano_right_object_contact_positions').reshape(T, -1, 3)
        assert np.allclose(C1[:, :3] - C0[:, :3], (w1 - w0)[:, None, :]) and np.allclose(C1[:, 3:], C0[:, 3:])
        box = ds.object_surface('box', f'{tmp}/meshes', 'mesh', P['obs_spacing'])
        ball = ds.object_surface('ball', f'{tmp}/meshes', 'mesh', P['obs_spacing'])
        gap = lambda O: np.array([ball.query(O[i, 1] + box.P[::4] - O[i, 0])[0].min() for i in range(T)])
        g0, g1 = gap(OP), gap(OP1)
        win = [(a, b) for a, b in ds.runs(role == 'X')]
        inside = np.concatenate([np.arange(a, b + 1 - P['fade']) for a, b in win])
        assert g0.min() < -0.01 and g1[inside].min() > 0.5 * P['margin'], (g0.min(), g1[inside].min())
        assert not any(w['stalled'] for w in rep['hands']['right'])


def test_end_to_end_head_on_is_left_unchanged():
    import pyarrow.parquet as pq
    with tempfile.TemporaryDirectory() as tmp:
        path, OP = _synthetic_reference(tmp, ball_y=0.005)
        t = pq.read_table(path)
        new, rep, lab = ds.modulate_reference(t, path, f'{tmp}/meshes', f'{tmp}/urdf',
                                              f'{tmp}/ref/reconstructed_stage/x_support.usda', P, geom='mesh')
        w = [x for x in rep['hands']['right'] if x['kind'] == 'A'][0]
        assert w['stalled'] and w['max_dev_m'] == 0.0
        assert np.array_equal(ds.col(t, 'robot_right_wrist_position'), ds.col(new, 'robot_right_wrist_position'))


def test_apply_delta_transport_moves_held_object_and_contacts():
    import pyarrow as pa
    T = 5
    cols = dict(object_body_position=np.zeros((T, 2, 3)).tolist(), object_root_position=np.zeros((T, 3)).tolist())
    for s in ('left', 'right'):
        cols[f'robot_{s}_wrist_position'] = np.zeros((T, 3)).tolist(); cols[f'robot_{s}_frames'] = np.zeros((T, 2, 7)).tolist()
        cols[f'mano_{s}_object_contact_positions'] = np.zeros((T, 4, 3)).tolist()
        pid = np.zeros((T, 4), int); pid[:, :2] = 2; cols[f'mano_{s}_object_contact_part_ids'] = pid.tolist()
    t = pa.table({k: [v] for k, v in cols.items()})
    d = {'left': np.zeros((T, 3)), 'right': np.zeros((T, 3))}; d['right'][1:4] = [0.01, 0.02, 0.0]
    lab = {'left': dict(role=np.array(['-'] * T), target=-np.ones(T, int)),
           'right': dict(role=np.array(['A', 'A', 'X', 'X', '-']), target=np.array([1, 1, 1, 1, 1]))}
    new = ds.apply_delta(t, d, lab, ['a', 'b'])
    OP = ds.col(new, 'object_body_position').reshape(T, 2, 3); C = ds.col(new, 'mano_right_object_contact_positions').reshape(T, 4, 3)
    assert np.allclose(OP[2:4, 1], [0.01, 0.02, 0]) and np.allclose(OP[[0, 1, 4]], 0) and np.allclose(OP[:, 0], 0)
    assert np.allclose(C[2:4, :2], [0.01, 0.02, 0]) and np.allclose(C[:, 2:], 0) and np.allclose(C[[0, 1, 4]], 0)
    assert np.allclose(ds.col(new, 'robot_right_frames').reshape(T, 2, 7)[1:4, :, :3], [0.01, 0.02, 0])
    assert np.allclose(ds.col(new, 'object_root_position'), 0)        # body 0 is not the held one


def test_phase_labels_transport_and_two_handed():
    """Box (index 1) held by the right hand f10-29, lifted 20 cm clear of the table; the left hand joins f25-29."""
    T = 40
    box = ds.SampledSurface.from_mesh(*_box_mesh(0.06), 0.004, 'box'); ball = sphere_surface(0.03, 0.004)
    OP = np.zeros((T, 2, 3)); OP[:, 0] = [0.5, 0.5, 0.63]; OP[:, 1] = [0, 0, 0.63]
    OP[12:28, 1, 2] += np.r_[np.linspace(0, 0.2, 8), np.full(8, 0.2)]
    OP[28:, 1, 2] = 0.63
    OR = np.tile(np.eye(3), (T, 2, 1, 1))
    hw = {s: np.tile([[-0.3 if s == 'left' else 0.3, 0.0, 0.7]], (T, 1, 1)) for s in ('left', 'right')}
    phases = [dict(hand='right', object='box', start=10, end=30), dict(hand='left', object='box', start=25, end=30)]
    lab = ds.phase_labels(None, T, ['ball', 'box'], hw, [ball, box], OP, OR, 0.60, P['d_pre'], phases=phases)
    r = lab['right']['role']
    assert (r[10:30] != 'A').all() and (r[:10] == 'A').all()      # hand 30 cm from the box: free frames are approach
    assert ('X' in r[14:25]) and (r[10:13] == '-').all()           # lift-off zone not modulated, carry is
    assert (r[25:30] == '-').all()                                 # two-handed: never modulated
    assert (lab['right']['held'][10:30] == 1).all() and lab['right']['held'][5] == -1


def test_phase_labels_release_zone_between_holds():
    """Right hand holds the box f5-9, releases it, then reaches for the ball (hold f30-34). Right after the release the
    hand is still next to the box: release zone, not modulated, although it is far from its next target."""
    T = 40
    box = ds.SampledSurface.from_mesh(*_box_mesh(0.06), 0.004, 'box'); ball = sphere_surface(0.03, 0.004)
    OP = np.zeros((T, 2, 3)); OP[:, 0] = [0.5, 0.0, 0.63]; OP[:, 1] = [0.0, 0.0, 0.63]
    OP[6:9, 1, 2] += 0.02                                          # the box is carried (hold_phases' rule)
    OR = np.tile(np.eye(3), (T, 2, 1, 1))
    x = np.r_[np.full(10, 0.0), np.linspace(0.0, 0.5, 20), np.full(10, 0.5)]
    hw = {'right': np.stack([[[xx, 0.0, 0.70]] for xx in x]), 'left': np.tile([[-0.5, 0.5, 0.7]], (T, 1, 1))}
    phases = [dict(hand='right', object='box', start=5, end=10), dict(hand='right', object='ball', start=30, end=35)]
    lab = ds.phase_labels(None, T, ['ball', 'box'], hw, [ball, box], OP, OR, 0.60, P['d_pre'], phases=phases)
    r = lab['right']['role']; tgt = lab['right']['target']
    assert (r[10:12] == '-').all() and (tgt[10:30] == 0).all()     # release zone; target = the next hold's object
    assert 'A' in r[14:24] and (r[27:30] == '-').all()             # free between the zones; grasp zone before f30


def _box_mesh(a):
    import trimesh
    m = trimesh.creation.box((a, a, a)); return m.vertices, m.faces


# ----------------------------------------------------------------------------- the phase-2 evaluation's pure parts
def _eval():
    sp = importlib.util.spec_from_file_location('eval_ds', os.path.join(REPO, 'docs', 'research', 'work',
                                                                         'ds-modulation-20261113', 'eval_ds.py'))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def _S(Po, Pc, Pd, Dc, Dd, guard=None, ends=True):
    base = dict(TG=20, HH=4, OOX=10, ends_ok=True)
    S = {'orig': dict(base, P=Po, D95_cm=0.0), 'clear': dict(base, P=Pc, D95_cm=Dc), 'ds': dict(base, P=Pd, D95_cm=Dd)}
    if guard:
        S['ds'][guard] = 100
    S['ds']['ends_ok'] = ends
    return S


def test_verdict_rules():
    v = _eval().verdict
    assert v(_S(9, 0, 0, 1.0, 0.1))[0] == 'NOT_APPLICABLE'
    assert v(_S(100, 40, 40, 2.0, 1.0))[0] == 'PASS'                  # R 0.6 = R_clear, less distortion
    assert v(_S(100, 20, 45, 2.0, 1.0))[0] == 'INCONCLUSIVE'          # R 0.55 < R_clear - 0.10 = 0.7
    assert v(_S(100, 40, 85, 2.0, 1.0))[0] == 'FAIL'                  # R 0.15 < 0.2
    assert v(_S(100, 40, 60, 2.0, 2.5))[0] == 'FAIL'                  # dominated: fewer removed and more distortion
    assert v(_S(100, 40, 60, 2.0, 1.0))[0] == 'INCONCLUSIVE'          # R 0.4: between the bars
    assert v(_S(100, 40, 40, 2.0, 1.0, guard='TG'))[0] == 'FAIL'      # new target penetrations
    assert v(_S(100, 40, 40, 2.0, 1.0, ends=False))[0] == 'FAIL'      # goal or outside-window frames changed


def test_classify_target_vs_non_target():
    C = _eval().classify
    M = dict(objects=['lid', 'pot'], frames=2, rows=[
        dict(hands={'left': {'pot': 0.004, 'lid': 0.010}, 'right': {'hand': 0.003}}, objects={'lid|pot': 0.02}),
        dict(hands={'left': {'lid': 0.001}, 'right': {}}, objects={})])
    ph = {'left': dict(role='AX', target=[0, 0]), 'right': dict(role='--', target=[-1, -1])}
    c = C(M, ph)
    assert np.allclose(c['nt'], [0.004, 0.0, 0.0, 0.0])                # frame-major (t, hand): the pot is non-target
    assert np.allclose(c['tg'], [0.010, 0.0, 0.001, 0.0]) and np.allclose(c['hh'], [0, 0.003, 0, 0])
    assert c['win'].tolist() == [True, False, True, False] and np.allclose(c['oo_x'], [0.0])


def test_ends_unchanged_guard():
    import pyarrow as pa, pyarrow.parquet as pq
    E = _eval(); T = 6
    with tempfile.TemporaryDirectory() as tmp:
        def write(name, dl):
            cols = {f'robot_{s}_wrist_position': (np.zeros((T, 3)) + (dl if s == 'left' else 0)).tolist() for s in ('left', 'right')}
            pq.write_table(pa.table({k: [v] for k, v in cols.items()}), f'{tmp}/{name}.parquet')
        ph = {'left': dict(role='-AAAA-'), 'right': dict(role='------')}
        mid = np.zeros((T, 3)); mid[2:4] = 0.01; write('o', np.zeros((T, 3))); write('ok', mid)
        bad = mid.copy(); bad[4] = 0.01; write('bad_end', bad)
        out = mid.copy(); out[0] = 0.01; write('bad_out', out)
        assert E.ends_unchanged(f'{tmp}/ok.parquet', f'{tmp}/o.parquet', ph)
        assert not E.ends_unchanged(f'{tmp}/bad_end.parquet', f'{tmp}/o.parquet', ph)
        assert not E.ends_unchanged(f'{tmp}/bad_out.parquet', f'{tmp}/o.parquet', ph)


if __name__ == '__main__':
    fails = 0
    for name, fn in sorted((k, v) for k, v in globals().items() if k.startswith('test_') and callable(v)):
        try:
            fn(); print('PASS', name)
        except Exception as e:                                       # noqa: BLE001
            fails += 1; print('FAIL', name, repr(e))
    sys.exit(1 if fails else 0)
