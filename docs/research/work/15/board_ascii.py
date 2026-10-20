"""ASCII occupancy of each wooden piece in the board plane (y,z), 8 mm cells; 'o' = marker-ball cell (x beyond board)."""
import trimesh, glob, numpy as np
for n in ['wooden_piece_1','wooden_piece_2']:
    m = trimesh.load(glob.glob(f'data/track_3/public/mesh/{n}/{n}_visual.glb')[0], force='mesh')
    P, _ = trimesh.sample.sample_surface(m, 200000, seed=0)
    xs = P[:,0]; med = np.median(xs)
    c = 0.008; y0, z0 = P[:,1].min(), P[:,2].min()
    iy = ((P[:,1]-y0)/c).astype(int); iz = ((P[:,2]-z0)/c).astype(int)
    G = np.full((iz.max()+1, iy.max()+1), '.', dtype='<U1')
    for a,b,x in zip(iz, iy, xs):
        if abs(x-med) > 0.008: G[a,b] = 'o'
        elif G[a,b] == '.': G[a,b] = '#'
    print(n, 'board-plane x median', round(med,4), 'rows=z (bottom first), cols=y')
    for r in G: print(''.join(r))
