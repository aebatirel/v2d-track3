"""G3 Pixal3D-MV final view sets, the 29 Oct assemble_views.py rule (S/gen/assemble_views.py) on G3's folders:
skin-gated set (views_sk) for non-skin-coloured objects unless its view 0 mask/silhouette IoU < 0.75, then the at-rest
set (views_rest); other objects: views_rest. Extra views with mask/silhouette IoU < 0.75 are dropped (view 0 is kept:
it defines the frame). GT-free (our masks and our posed library_v3 silhouettes only).
Usage: assemble_g3.py OUT   (reads OUT/views_sk, OUT/views_rest; writes OUT/views_final/<set>, selection.json)
"""
import json, os, shutil, sys

SKIN = {'white_pot', 'white_pot_lid', 'blue_cup', 'water_pitcher', 'plastic_dish_rack', 'mini_dust_pan'}
root = sys.argv[1]
out = os.path.join(root, 'views_final'); os.makedirs(out, exist_ok=True); rep = {}
names = sorted(set(os.listdir(os.path.join(root, 'views_sk'))) | set(os.listdir(os.path.join(root, 'views_rest'))))
for d in names:
    obj = d.split('_', 1)[1]
    src = 'views_rest'
    p3 = os.path.join(root, 'views_sk', d, 'probe_meta.json')
    if obj in SKIN and os.path.exists(p3) and json.load(open(p3))['chosen'][0]['iou_sil_mask'] >= 0.75:
        src = 'views_sk'
    sd = os.path.join(root, src, d)
    if not os.path.exists(os.path.join(sd, 'probe_meta.json')):
        rep[d] = dict(src=src, error='no view set'); continue
    meta = json.load(open(os.path.join(sd, 'probe_meta.json'))); T = json.load(open(os.path.join(sd, 'transforms.json')))
    keep = [i for i, c in enumerate(meta['chosen']) if i == 0 or c['iou_sil_mask'] >= 0.75]
    od = os.path.join(out, d); os.makedirs(od, exist_ok=True)
    T['frames'] = [T['frames'][i] for i in keep]
    meta['chosen'] = [meta['chosen'][i] for i in keep]; meta['source'] = src
    for fr in T['frames']:
        shutil.copy(os.path.join(sd, fr['file_path']), od)
    json.dump(T, open(os.path.join(od, 'transforms.json'), 'w'), indent=1)
    json.dump(meta, open(os.path.join(od, 'probe_meta.json'), 'w'), indent=1)
    shutil.copy(os.path.join(sd, 'montage.jpg'), os.path.join(od, f'montage_{src}.jpg'))
    rep[d] = dict(src=src, views=[(c['k'], c['iou_sil_mask'], c['rest']) for c in meta['chosen']])
print(json.dumps(rep))
json.dump(rep, open(os.path.join(out, 'selection.json'), 'w'), indent=1)
