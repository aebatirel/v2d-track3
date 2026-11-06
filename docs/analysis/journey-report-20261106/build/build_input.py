import json,os
R=os.path.dirname(os.path.abspath(__file__)); D=f'{R}/digests'
order=[('EXACT KAGGLE SUBMISSION HISTORY (from the Kaggle API; authoritative for board scores)',None),
 ('Leaderboard and submissions domain digest','cached_leaderboard.md'),
 ('Perception domain digest','cached_perception.md'),
 ('Work log digest, slice 1','worklog_part1.md'),('Work log digest, slice 2','worklog_part2.md'),
 ('Work log digest, slice 3','worklog_part3.md'),('Work log digest, slice 4','worklog_part4.md'),
 ('Work log digest, slice 5','worklog_part5.md'),
 ('Analysis reports digest, part 1','reports_part1.md'),('Analysis reports digest, part 2','reports_part2.md'),
 ('Research notes digest (26 deep-research notes)','research_notes.md'),
 ('Chat: main early session, 20–24 Oct, and the builder session','chats_main2.md'),
 ('Chat: main early session, 24–27 Oct','chats_main.md'),
 ('Chat: Rust rewrite evaluation (22 Oct)','cached_chat_rust.md'),
 ('Chat: contact-slot labels, $100 eval rerun, third submission (25–27 Oct)','cached_chat_contactslots.md'),
 ('Chat: robustness review (26–27 Oct)','cached_chat_robustness.md'),
 ('Chat: 14 lane sessions (newest results of each)','chats_lanes.md'),
 ('Coordinator session: owner messages, 30 Oct – 3 Nov','coordinator_owner_msgs.md')]
out=[]
for title,fn in order:
    if fn is None:
        subs=json.load(open(f'{R}/subs_timeline.json'))
        t='| uploaded UTC | AUC | SP-SR | MP-SR | RPE cm | MPPE cm | CD-O | description |\n|---|---|---|---|---|---|---|---|\n'
        for s in subs: t+=f"| {s['date']} | {s.get('auc','-')} | {s.get('sp-sr','-')} | {s.get('mp-sr','-')} | {s.get('rpe','-')} | {s.get('mppe','-')} | {s.get('cd-o','-')} | {s['desc'].replace('KURSAD','a team member')} |\n"
        lb=json.loads(open(f'{R}/lb_now.txt').read().strip().splitlines()[-1])
        t+='\nLeaderboards read 2026-11-06 ~06:15 UTC (top 20 per board): \n'
        for b,rows in lb.items(): t+=f"- {b}: top3 {rows[:3]}; us {[r for r in rows if 'Imitation' in r[1]]}\n"
        t+='- Rank sums among teams in all six top-20s: richchentw 7, DDD 15, rlwrld 23, Zihao Guo 24, SRL 37, Barry Allen 46, Purple 47, Imitation.Tech 56, DSAIL 61. (On 3 Nov 10:33 UTC ours was 45, 7th.)\n'
        t+='- Each board keeps each team\'s best submission, so packs 13h, 13i, 13j were CD-O-only variants that deliberately traded AUC for CD-O; 14p remains the best on the five pose boards.\n'
    else:
        p=f'{D}/{fn}'
        if not os.path.exists(p): continue
        t=open(p).read()
    out.append(f'\n\n################ {title} ################\n\n{t}')
s=''.join(out).replace('KURSAD','a team member')
open(f'{R}/synthesis_input.md','w').write(s); print(len(s), len(s.split()))
