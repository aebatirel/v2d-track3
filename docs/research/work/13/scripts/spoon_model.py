"""Parametric wooden spoon + 3 mocap markers (as seen in eval videos), exact surface moments, frame-rule predictions.
Spoon body frame used for construction ("physical frame" P):
  z_P: long axis, bowl tip (s=0) -> handle end (s=L)
  x_P: toward the CONVEX back of the bowl (bowl interior opens toward -x_P)
  y_P = z_P x x_P  (right-handed): M1 (marker at the bowl-neck junction) sits on +y_P, M2 on -y_P (video, [V])
Frame F_A := published x points to the convex back (+x_P side); F_B := roll by 180 deg about z.
"""
import numpy as np

def sphere(center, r, n=24, keep_dir=None, keep_frac=1.0):
    th = np.linspace(0, np.pi, n); ph = np.linspace(0, 2*np.pi, 2*n, endpoint=False)
    T, P = np.meshgrid(th, ph, indexing="ij")
    D = np.stack([np.sin(T)*np.cos(P), np.sin(T)*np.sin(P), np.cos(T)], -1).reshape(-1, 3)
    V = center + r*D
    idx = np.arange(n*2*n).reshape(n, 2*n); F = []
    for i in range(n-1):
        a = idx[i]; b = idx[i+1]; a2 = np.roll(a, -1); b2 = np.roll(b, -1)
        F += [np.stack([a, b, b2], 1), np.stack([a, b2, a2], 1)]
    F = np.concatenate(F)
    if keep_dir is not None and keep_frac < 1.0:
        # drop the cap facing -keep_dir so that kept area fraction = keep_frac (cap area frac = (1-cos a)/2)
        c = 1 - 2*(1-keep_frac)   # keep points with D.keep_dir > -c  ... area frac kept = (1+c)/2
        cen = D[F].mean(1)
        F = F[cen @ keep_dir > -c]
    return V, F

def cylinder(p0, p1, r, n=24):
    ax = p1 - p0; L = np.linalg.norm(ax); ax = ax/L
    u = np.cross(ax, [1, 0, 0]) if abs(ax[0]) < 0.9 else np.cross(ax, [0, 1, 0]); u /= np.linalg.norm(u); v = np.cross(ax, u)
    ph = np.linspace(0, 2*np.pi, n, endpoint=False)
    ring = r*(np.cos(ph)[:, None]*u + np.sin(ph)[:, None]*v)
    V = np.concatenate([p0 + ring, p1 + ring]); i = np.arange(n); j = (i+1) % n
    F = np.concatenate([np.stack([i, j, n+j], 1), np.stack([i, n+j, n+i], 1)])
    return V, F

def spoon_body(L=0.33, Lb=0.095, wb=0.032, wn=0.0085, we=0.0125, tb=0.0045, th=0.011, Db=0.009,
               neck=0.025, ns=500, nphi=72, asym_y=0.0, handle_off_x=0.0):
    """Closed lofted spoon. Returns V,F, half-width fn, centre-x fn (handle mid-plane offset)."""
    s = np.linspace(0.0, L, ns)
    u = np.clip((s - Lb/2)/(Lb/2), -1, 1)
    wbowl = wb*np.sqrt(np.clip(1 - u**2, 0, None))
    # handle half-width: neck minimum wn at s=Lb+neck*0.3, then linear to we near end
    sh = np.clip((s - Lb)/(L - Lb), 0, 1)
    wh = wn + (we - wn)*sh
    w = np.where(s < Lb*0.75, wbowl, np.maximum(wbowl, wh))
    endr = 0.010; k = np.clip((L - s)/endr, 0, 1); w = np.where(s > L - endr, wh*np.sqrt(1 - (1 - k)**2), w)
    w[0] = 0; w[-1] = 0
    # thickness: bowl shell tb, blending to handle th over the neck
    bl = np.clip((s - Lb*0.8)/neck, 0, 1)
    t = tb*(1 - bl) + th*bl
    t = np.minimum(t, 2*w + 1e-6)
    phi = np.linspace(0, 2*np.pi, nphi, endpoint=False)
    S, P = np.meshgrid(s, phi, indexing="ij")
    W = np.interp(S, s, w); Tt = np.interp(S, s, t)
    cy = np.cos(P); sx = np.sin(P)
    U = (S - Lb/2)/(Lb/2)
    D = Db*np.clip(1 - cy**2 - U**2, 0, None)          # dish: interior opens toward -x
    X = 0.5*Tt*sx + D + handle_off_x*np.clip((S - Lb)/(L - Lb), 0, 1)   # convex back bulges to +x
    Y = W*cy*(1 + asym_y*cy)                           # optional mirror asymmetry
    V = np.stack([X, Y, S], -1).reshape(-1, 3)
    idx = np.arange(ns*nphi).reshape(ns, nphi); F = []
    for i in range(ns - 1):
        a = idx[i]; b = idx[i+1]; a2 = np.roll(a, -1); b2 = np.roll(b, -1)
        F += [np.stack([a, b, b2], 1), np.stack([a, b2, a2], 1)]
    F = np.concatenate(F)
    T = V[F]; ar = 0.5*np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    halfw = lambda z: np.interp(z, s, w)
    return V, F[ar > 1e-14], halfw

def assemble(parts):
    Vs, Fs, off = [], [], 0
    for V, F in parts:
        Vs.append(V); Fs.append(F + off); off += len(V)
    return np.concatenate(Vs), np.concatenate(Fs)

def spoon_with_markers(p):
    V, F, halfw = spoon_body(**p["body"])
    parts = [(V, F)]
    r = p.get("r_marker", 0.0072); base_h = p.get("base_h", 0.004); rb = p.get("base_r", 0.0055)
    kf = p.get("keep_frac", 0.75)
    xm = p.get("marker_x", 0.0)
    for name, side in (("m1", +1), ("m2", -1)):
        z = p[name + "_z"]
        y_edge = side*(halfw(z) + p.get(name + "_extra", 0.0))
        xmi = xm + p.get(name + "_dx", 0.0)
        c_base0 = np.array([xmi, y_edge, z]); c_base1 = np.array([xmi, y_edge + side*base_h, z])
        c_sph = np.array([xmi, y_edge + side*(base_h + r*0.85), z])
        if p.get("bases", True):
            parts.append(cylinder(c_base0, c_base1, rb))
        parts.append(sphere(c_sph, r, keep_dir=np.array([0, side, 0.0]), keep_frac=kf))
    if p.get("m3", True):
        L = p["body"].get("L", 0.33)
        c0 = np.array([xm, 0, L - 0.001]); c1 = np.array([xm, 0, L + base_h])
        if p.get("bases", True): parts.append(cylinder(c0, c1, rb))
        parts.append(sphere(np.array([xm, 0, L + base_h + r*0.85]), r, keep_dir=np.array([0, 0, 1.0]), keep_frac=kf))
    return assemble(parts)

def h2(a, b, c): return a*a + b*b + c*c + a*b + a*c + b*c
def h3(a, b, c): return a**3 + b**3 + c**3 + a*a*b + a*a*c + b*b*a + b*b*c + c*c*a + c*c*b + a*b*c

def frame_and_skews(V, F):
    """Exact R1 frame (unsigned axes) and per-axis exact skews, expressed against the construction axes."""
    T = V[F]; area = 0.5*np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); A = area.sum()
    s = T.sum(1); c = (area[:, None]*s/3).sum(0)/A
    M2 = (np.einsum("n,ni,nj->ij", area, T[:, 0], T[:, 0]) + np.einsum("n,ni,nj->ij", area, T[:, 1], T[:, 1])
          + np.einsum("n,ni,nj->ij", area, T[:, 2], T[:, 2]) + np.einsum("n,ni,nj->ij", area, s, s))/12/A
    C = M2 - np.outer(c, c)
    w, E = np.linalg.eigh(C)
    # orient each eigenvector to agree with the construction axis it is closest to (x_P, y_P, z_P)
    for i in range(3):
        if E[i, i] < 0: E[:, i] *= -1
    sk = []
    for i in range(3):
        f = (T - c) @ E[:, i]
        m2 = (area*h2(*f.T)/6).sum()/A; m3 = (area*h3(*f.T)/10).sum()/A
        sk.append(m3/m2**1.5)
    return c, w, E, np.array(sk), A

def predict(sk):
    """Given skews along construction-aligned axes (x_P, y_P, z_P), return published-frame choice per rule.
    'A' = +x toward convex back (x_P), 'B' = opposite roll. Assumes z rule gives z_P (checked separately)."""
    sx, sy, sz = sk
    out = {}
    out["skew_x"] = "A" if sx > 0 else "B"
    out["skew_y"] = "A" if sy > 0 else "B"            # y=+y_P <=> x=+x_P (given z=+z_P)
    out["hybrid0.02"] = out["skew_y"] if abs(sy) >= 0.02 else out["skew_x"]
    out["larger_abs"] = out["skew_x"] if abs(sx) >= abs(sy) else out["skew_y"]
    return out

if __name__ == "__main__":
    base = dict(body=dict(), m1_z=0.105, m2_z=0.155)
    V, F = spoon_with_markers(base)
    c, w, E, sk, A = frame_and_skews(V, F)
    print("nominal spoon+markers: area %.0f cm2, centroid z %.1f mm, std mm" % (A*1e4, c[2]*1e3), np.sqrt(w)*1e3)
    print("skews along (x_P,y_P,z_P):", sk.round(4), "axes tilt deg:", np.degrees(np.arccos(np.clip(np.abs(np.diag(E)), 0, 1))).round(3))
    print(predict(sk))
    Vb, Fb, _ = spoon_body()
    c, w, E, sk, A = frame_and_skews(Vb, Fb)
    print("bare spoon: area %.0f cm2, skews" % (A*1e4), sk.round(4), "std mm", (np.sqrt(w)*1e3).round(1))
