import json, sys, collections
S = sys.argv[1]; qa = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else None
P = json.load(open(f'{S}/qa/pairs.json'))
LAB = dict(white_pot='White pot', white_pot_lid='Pot lid', blue_cup='Blue cup', beige_cup='Beige cup', plastic_dish_rack='Dish rack',
           mini_sweeper='Mini sweeper', mini_dust_pan='Mini dust pan', water_pitcher='Water pitcher', wooden_piece_1='Board 1',
           wooden_piece_2='Board 2', wooden_spoon='Wooden spoon')
qa_map = {}
if qa:
    for r in qa['pairs']:
        qa_map[(r['episode'], r['object'])] = r
eps = collections.OrderedDict()
order = [l.split() for l in open(f'{S}/eval_pairs.txt')]
for e, o in order:
    v = P[f'{e}:{o}']; e = int(e)
    src = 'library_v3x' if (e == 8 and o == 'beige_cup') else ('template' if o == 'wooden_spoon' else 'library_v3')
    rec = dict(label=LAB[o], obj=o, img=v['img'], frame=v['frame'], w=v['w'], h=v['h'], source=src)
    q = qa_map.get((e, o))
    if q:
        cls = dict(good='good', minor='warn', poor='bad')[q['fit']]
        verdict = dict(good='fits', minor='minor issues', poor='poor fit')[q['fit']]
        rec['qa'] = dict(cls=cls, verdict=verdict, text=q['summary'])
    eps.setdefault(e, []).append(rec)
json.dump([dict(episode=e, objects=objs) for e, objs in eps.items()], open(f'{S}/page/eval.json', 'w'))
print(len(eps), 'episodes')
