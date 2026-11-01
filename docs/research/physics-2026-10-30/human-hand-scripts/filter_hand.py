import sys, re, xml.etree.ElementTree as ET
arm = sys.argv[1]
HAND = set("ECRL ECRB ECU FCR FCU PL PT PQ FDS5 FDS4 FDS3 FDS2 FDP5 FDP4 FDP3 FDP2 EDC5 EDC4 EDC3 EDC2 EDM EIP EPL EPB FPL APL OP RI2 LU_RB2 UI_UB2 RI3 LU_RB3 UI_UB3 RI4 LU_RB4 UI_UB4 RI5 LU_RB5 UI_UB5".split())
mus = ET.parse(f'{arm}/assets/myoarm_r_muscle.xml').getroot()
keep_t = set()
for parent in mus.iter():
    for ch in list(parent):
        if ch.tag in ('general','muscle'):
            if ch.get('name') in HAND: keep_t.add(ch.get('tendon'))
            else: parent.remove(ch)
ET.ElementTree(mus).write(f'{arm}/assets/hand_only_muscle.xml')
ten = ET.parse(f'{arm}/assets/myoarm_r_tendon.xml').getroot()
for parent in ten.iter():
    for ch in list(parent):
        if ch.tag in ('spatial','fixed') and ch.get('name') not in keep_t: parent.remove(ch)
ET.ElementTree(ten).write(f'{arm}/assets/hand_only_tendon.xml')
# equality constraints in assets reference shoulder joints: fine (joints exist in chain)
print(len(keep_t), 'tendons kept')
