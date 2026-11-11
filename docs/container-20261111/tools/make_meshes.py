"""Lay out meshes/track3_13h/episode_XXXXXX/<object>.glb from the 13h commit tree, one byte copy per (episode, object)
pair of build_13h/swap_manifest.json, and check every md5 against the manifest's md5_after."""
import hashlib, json, shutil, subprocess, sys
from pathlib import Path
manifest, code, out = json.load(open(sys.argv[1])), Path(sys.argv[2]), Path(sys.argv[3])
# 13h-tree source of each md5 (all in the clean checkout at 9610329e)
src = {
 '5243c309b6758f682b62e29ade6ff34f': 'meshes/g2_pack13h/white_pot.glb',
 'ab012e4e0add44c3923fd172c4639734': 'meshes/g2_pack13h/blue_cup.glb',
 'a289d009c45c6ee09d7dd787b8e7dbcf': 'meshes/g2_pack13h/plastic_dish_rack.glb',
 '35727a10bca407594f41d108b4dc03ab': 'meshes/c0_pack9a/white_pot_lid.glb',
 '68dcf0495c23d2213b1ec4a35b8ad423': 'meshes/library_v3/wooden_spoon.glb',
 '8c8be2b0747d234706913a2360e90570': 'meshes/c1_pack9aplus/beige_cup.glb',
 '55fe1682f09721ca5d4e98477bfef150': 'meshes/tierB_pack12e/mini_sweeper.glb',
 '1530b1d3be77507730b00e1c5047cad1': 'meshes/tierBplus_pack13f/mini_dust_pan.glb',
 'e59c15a3e4a442ebc52e7cd72ab73124': 'meshes/tierB_pack12e/water_pitcher.glb',
 '015aaae3183760cd8a48d82b5599d32c': 'meshes/tierB_pack12e/wooden_piece_1.glb',
 'bf82e385cac24a586168b4f14bf5b245': 'meshes/tierB_pack12e/wooden_piece_2.glb',
}
rec = []
for p in manifest['pairs']:
    want = p['md5_after']; s = code / src[want]
    assert hashlib.md5(s.read_bytes()).hexdigest() == want, s
    dst = out / p['file'].split('meshes/', 1)[1]
    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(s, dst)
    got = hashlib.md5(dst.read_bytes()).hexdigest()
    rec.append(dict(episode=p['episode'], slot=p['slot'], object=p['object'], file=str(dst.relative_to(out)), source=src[want], md5=got, expected=want, ok=got == want))
bad = [r for r in rec if not r['ok']]
print(f'{len(rec)} mesh files, {len(bad)} mismatches')
json.dump(rec, open(sys.argv[4], 'w'), indent=1)
sys.exit(1 if bad else 0)
