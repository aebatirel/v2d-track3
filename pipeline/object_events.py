"""Object action-phase events from OUR object track (2026-10-25, owner: "separate the problem into bits ... know when the
release happens; mind the boundaries"; docs/research/approaches-2026-10-25/approach3-grasp-taxonomy.md §6).
Humans run grasps as action phases separated by contact events (Johansson & Flanagan 2009): load before lift-off,
unload after touchdown. Our MANO contact labels time a hold 24 frames early to 22 late and end it 26-116 frames after
the object is placed (public twins vs mocap), while the object track times lift-off within 1 frame on 5 of 6 objects.
So the grasp windows are anchored on the object's own events:
  liftoff  first frame t >= the rest start PE whose origin is > LIFT_CM above its height at PE for 3 consecutive frames;
  settle   the frame after the object's LAST movement (speed >= STILL_CM cm/frame or turn >= STILL_DEG deg/frame) in
           [liftoff, hold end), accepted as a placement only if it then stays still for >= RUN frames, came down >= 1 cm
           from its peak since lift-off, and either stays still to the end of the episode or is back within NEAR_CM of
           its rest height (a hand-over or an object held still in the air is not a placement).
Only our reference is read (no ground truth)."""
import numpy as np

LIFT_CM, STILL_CM, STILL_DEG, RUN, NEAR_CM = 1.5, 0.5, 2.0, 5, 3.0


def moving(P, R):
    """(T,) bool: the object moves at frame t (vs t-1). P (T,3) m, R scipy Rotation (T)."""
    v = np.r_[0.0, np.linalg.norm(np.diff(P, axis=0), axis=1) * 100]
    w = np.r_[0.0, np.degrees((R[1:] * R[:-1].inv()).magnitude())]
    return (v >= STILL_CM) | (w >= STILL_DEG)


def hold_events(P, R, pe, s1):
    """Lift-off and settle frames for a hold that ends at s1 (exclusive), the object resting from pe; None if absent."""
    T = len(P); zr = (P[:, 2] - P[pe, 2]) * 100
    lift = next((t for t in range(pe, max(pe, min(s1, T) - 2)) if (zr[t:t + 3] > LIFT_CM).all()), None)
    if lift is None:
        return None, None
    mv = moving(P, R); idx = np.nonzero(mv[lift:min(s1, T)])[0]
    settle = lift + int(idx[-1]) + 1 if len(idx) else lift + 1
    if settle + RUN > T or mv[settle:settle + RUN].any() or zr[settle] > zr[lift:settle + 1].max() - 1.0:
        return lift, None
    if not ((~mv[settle:]).all() or abs(zr[settle]) < NEAR_CM):
        return lift, None
    return lift, settle
