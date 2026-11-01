"""Summarise two third-party hand models (read as data): D-Grasp's MANO URDF and HOIC's MuJoCo hand.
usage: python -I probe_dgrasp_hoic.py mano_mean_meshcoll.urdf eval_model_tmp.xml"""
import sys, xml.etree.ElementTree as ET
from collections import Counter
u = ET.parse(sys.argv[1]).getroot()
print('D-Grasp URDF: joints by type', Counter(j.get('type') for j in u.findall('joint')))
for j in u.findall('joint'):
    if j.get('type') == 'fixed': continue
    lim = j.find('limit'); ax = j.find('axis')
    print('  ', j.get('name'), j.get('type'), ax.get('xyz') if ax is not None else '', lim.get('lower'), lim.get('upper'), 'effort', lim.get('effort'))
print('  total mass kg', round(sum(float(l.find('inertial/mass').get('value')) for l in u.findall('link') if l.find('inertial/mass') is not None), 4))
print('  collision meshes', sorted({c.find('geometry/mesh').get('filename') for l in u.findall('link') for c in l.findall('collision') if c.find('geometry/mesh') is not None}))
h = ET.parse(sys.argv[2]).getroot()
print('HOIC MJCF: option', h.find('option').attrib)
for d in h.iter('default'):
    for ch in d:
        if ch.tag in ('geom', 'joint') and d.get('class') == 'robot0:asset_class': print('  default', ch.tag, ch.attrib)
for j in h.iter('joint'):
    if (j.get('name') or '').startswith('robot0:'): print('  ', j.get('name'), j.get('type', 'hinge'), j.get('axis'), j.get('range'))
for g in h.iter('geom'):
    if (g.get('name') or '').startswith('robot0:C_'): print('  ', g.get('name'), g.get('type'), 'size', g.get('size'))
