import json,glob,sys
for f in sys.argv[1:]:
    d=json.load(open(f)); print('=====',f.split('/')[-1], 'anchor', d['alignment_anchor'], '| meshes', d.get('meshes_A','')[-12:], d.get('meshes_B','')[-12:])
    if d.get('registration_B'): print('   regB', d['registration_B'])
    for n,o in d['per_object'].items():
        print(' ',n, {k:o[k] for k in ['AUC_A','AUC_B','dAUC','dAUC_frame0','dAUC_translation_only','dAUC_rotation_only','frames_worse','frames_better']})
        print('    f0',o['frame0'],'chg',o['change_B_minus_A'])
        print('    errA',o['error_A'],'errB',o['error_B'])
        for sg in o['segments_worse'][:3]: print('    worse',sg)
        for sg in o['segments_better'][:2]: print('    better',sg)
