"""Synthetic meshes for the self-ambiguity tests (B5). Pure trimesh recipes, no gmg import, so the one-off reference
script (build/b5/amb_reference.py, which runs scripts/mesh_metric.ambiguity outside the gmg) and tests/test_score.py
build exactly the same meshes. GT-free: primitives only, no file is read."""
import numpy as np
import trimesh

SLAB = (0.12, 0.07, 0.015)                      # a board-like slab, metres
# marker balls on posts (radius 10 mm: inside the generic 1.5-12.5 mm window of PREREG A.6, not a scan value), at
# asymmetric positions on the slab's top face: (x, y) on the face, post length above it. Fixture geometry chosen so
# the balls clearly break the slab's symmetry (the test checks the V5 rule's logic, not a detector): with 8 mm balls
# on 18-25 mm posts the slab is still flip-risk (amb 2.87 mm, floor 1.47 mm [M], B5 notes)
BALLS = ((0.045, 0.022, 0.028), (-0.030, 0.020, 0.035), (0.010, -0.025, 0.025), (-0.050, -0.010, 0.031))
BALL_R = 0.010
POST_R = 0.002


def slab():
    return trimesh.creation.box(SLAB)


def balls_on_posts(top=SLAB[2] / 2, balls=BALLS, r=BALL_R):
    parts, centres = [], []
    for x, y, h in balls:
        post = trimesh.creation.cylinder(radius=POST_R, height=h, sections=16)
        post.apply_translation([x, y, top + h / 2 - 0.001])
        ball = trimesh.creation.icosphere(subdivisions=2, radius=r)
        c = np.array([x, y, top + h + r * 0.6])
        ball.apply_translation(c)
        parts += [post, ball]
        centres.append(c)
    return parts, np.asarray(centres)


def slab_with_balls():
    """Manifold union of the slab and its balls on posts (the markers' attach rule of SPEC section 10)."""
    parts, _ = balls_on_posts()
    m = trimesh.boolean.union([slab()] + parts, engine='manifold')
    return trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)


def cylinder():
    return trimesh.creation.cylinder(radius=0.04, height=0.08, sections=64)


def ell():
    """An L-shaped block (no proper symmetry)."""
    a = trimesh.creation.box((0.10, 0.03, 0.02))
    b = trimesh.creation.box((0.03, 0.07, 0.02)).apply_translation([0.035, 0.05, 0.0])
    m = trimesh.boolean.union([a, b], engine='manifold')
    return trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)


RECIPES = dict(slab=(slab, None), slab_balls=(slab_with_balls, None), cylinder_axial=(cylinder, 'axial'),
               cylinder_none=(cylinder, None), ell=(ell, None), slab_half=(slab, 'half'))
