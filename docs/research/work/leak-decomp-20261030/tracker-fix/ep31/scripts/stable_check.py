"""Stable resting faces of our library_v3 sweeper (GT-free) and of the scan (oracle); where the true and perceived f0 poses lie."""
import sys, json, numpy as np, trimesh
sys.path.insert(0, sys.argv[1]); import diag31 as D; import stable as ST
XF = D.XF
names, gt, N, tr = D.load_tracks()
X = np.asarray(D.XG['mini_sweeper']['X_scan_T_lib'])[:3, :3]
n = np.array([-0.0782, -0.6593, -0.7478]); up = n   # our plane (depth0, det_rules), camera side = +n
for tag, path in (('lib', f'{D.REPO}/meshes/library_v3/mini_sweeper.glb'), ('scan', XF.scan_path(D.T3D, 'mini_sweeper'))):
    m = trimesh.load(path, force='mesh')
    sf, com = ST.stable_faces(m)
    downs = np.array([s['normal'] for s in sf])
    print(tag, 'stable facets', len(sf), 'areas cm2', [round(s['area'] * 1e4, 1) for s in sf[:8]])
    d_true_scan = gt['mini_sweeper'][0][:3, :3].T @ np.array([0, 0, -1.0])
    d_true = X.T @ d_true_scan if tag == 'lib' else d_true_scan
    ang = np.degrees(np.arccos(np.clip(downs @ d_true, -1, 1))); k = int(np.argmin(ang))
    print('  truth f0: nearest stable facet #%d area %.1f cm2 angle %.2f deg' % (k, sf[k]['area'] * 1e4, ang[k]))
    for arm in ('Po', 'Ps'):
        Rp = tr[arm]['mini_sweeper'][0][:3, :3]
        d_p = Rp.T @ (-up); d_p = X.T @ d_p if tag == 'lib' else d_p
        a2 = np.degrees(np.arccos(np.clip(downs @ d_p, -1, 1))); k2 = int(np.argmin(a2))
        print('  %s perceived f0: nearest stable facet #%d angle %.2f deg; that facet vs truth down %.2f deg; perceived-vs-true down %.2f deg'
              % (arm, k2, a2[k2], ang[k2], np.degrees(np.arccos(np.clip(d_p @ d_true, -1, 1)))))
