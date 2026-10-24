import sys, numpy as np, trimesh
np.set_printoptions(linewidth=200)
for p in sys.argv[1:]:
    m = trimesh.load(p, force='mesh')
    b = m.bounds; ext = b[1]-b[0]; ax = int(np.argmin(ext))  # thin axis in mesh frame
    o = [i for i in range(3) if i != ax]
    print(p.split('/')[-1], 'thin axis', 'xyz'[ax], 'extents', np.round(ext*100,2), 'cm')
    nx, ny = 23, 14
    g0 = np.linspace(b[0][o[0]]+0.003, b[1][o[0]]-0.003, nx); g1 = np.linspace(b[0][o[1]]+0.003, b[1][o[1]]-0.003, ny)
    T = np.full((ny, nx), np.nan); TOP = np.full((ny, nx), np.nan); BOT = np.full((ny, nx), np.nan)
    for i, a0 in enumerate(g0):
        for j, a1 in enumerate(g1):
            org = np.zeros(3); org[o[0]] = a0; org[o[1]] = a1; org[ax] = b[0][ax]-0.01
            d = np.zeros(3); d[ax] = 1
            loc, _, _ = m.ray.intersects_location([org], [d])
            if len(loc):
                h = np.sort(loc[:, ax])
                BOT[j, i] = h[0]; TOP[j, i] = h[-1]
                # solid thickness: sum of intervals (pairs)
                if len(h) % 2 == 0:
                    T[j, i] = sum(h[k+1]-h[k] for k in range(0, len(h), 2))
                else:
                    T[j, i] = h[-1]-h[0]
    print('  solid thickness mm (rows=%s, cols=%s):' % ('xyz'[o[1]], 'xyz'[o[0]]))
    print(np.round(T*1000).astype('float'))
    print('  top coord mm'); print(np.round(TOP*1000))
    print('  bottom coord mm'); print(np.round(BOT*1000))
    print('  median thickness mm', np.nanmedian(T)*1000, 'p10/p90', np.nanpercentile(T,10)*1000, np.nanpercentile(T,90)*1000, 'coverage', np.mean(~np.isnan(T)))
