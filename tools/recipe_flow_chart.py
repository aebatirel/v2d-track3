"""Flow chart of our Track 3 recipe as it runs on 26 Oct 2026 (for the owner; docs/recipe-flow.png). Matplotlib only.
Usage: python recipe_flow_chart.py OUT.png"""
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

C = dict(inp='#e8e8e8', per='#d6e6fb', hand='#dceefc', ref='#d3f0ea', asset='#fde7cc', A='#e6dcf7', B='#efdcf0',
         choice='#d9f2d0', pack='#d9d9e8', fix='#fff4c2', new='#ffd9d9', edge='#444444')
fig, ax = plt.subplots(figsize=(17, 22)); ax.set_xlim(0, 170); ax.set_ylim(0, 220); ax.axis('off')


def box(x, y, w, h, title, body, col, ls='-', tsize=12.5, bsize=10.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.6,rounding_size=2', fc=col, ec=C['edge'], lw=1.3, ls=ls))
    ax.text(x + w / 2, y + h - 2.6, title, ha='center', va='top', fontsize=tsize, weight='bold')
    ax.text(x + 2.2, y + h - 7.3, body, ha='left', va='top', fontsize=bsize, linespacing=1.35)


def arrow(x0, y0, x1, y1, ls='-', col='#333333', txt=None, rad=0.0):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='-|>', mutation_scale=18, lw=1.6, color=col, ls=ls,
                                 connectionstyle=f'arc3,rad={rad}'))
    if txt:
        ax.text((x0 + x1) / 2 + 1.2, (y0 + y1) / 2, txt, fontsize=9.5, color=col, va='center')


ax.text(85, 217, 'V2D Track 3: our per-episode recipe (as run on 26 Oct 2026)', ha='center', fontsize=19, weight='bold')
ax.text(85, 212.3, 'Same automatic pipeline for every eval episode. No ground truth is read anywhere; '
        'choices use our own reference only.', ha='center', fontsize=11.5)

box(22, 196, 126, 12, '0  Input (per eval episode)',
    'head-camera video (ego cams a = colour, b/c = stereo pair) + object names and slot order (kit roster)', C['inp'])
box(5, 160, 100, 31, '1  Perception (perc2): where is each object in every frame?',
    '- stereo depth (FoundationStereo on cams c/b)\n'
    '- detection at frame 0 (Grounding DINO + rules: on-table rule, re-proposal*)\n'
    '- 6-DoF tracking with OUR library meshes (FoundationPose), track guard*\n'
    '   (rejects tracks that jump to the wrist when the object is hidden)\n'
    '- camera motion (visual odometry) -> object poses in a world frame\n'
    '- identity rule* for look-alike objects (boards: marker knobs)', C['per'])
box(110, 160, 55, 31, '2  Hands',
    '- MediaPipe hand keypoints on cam a\n- lifted to 3-D with the stereo depth\n- bone-length-consistent refinement',
    C['hand'])
box(5, 128, 160, 25, '3  Reference (mkref): what the robot should reproduce',
    '- table frame; human hands retargeted to the Sharpa robot hands (IK, E2S); contacts\n'
    '- contact-anchored retargeting: fingertips put on the object surfaces ("mck")\n'
    '- the object trajectory in this reference is what the policy tracks and what our own score (sim_vs_ref) compares against',
    C['ref'])
box(5, 101, 160, 20, '4  Simulator assets: the bodies FlashCHORD simulates',
    '- our library meshes (library_v3; v3x for eval 8) -> URDFs, mass 0.3 kg, inertia from the mesh\n'
    '- support fill / arc foot* so resting objects stand;  collision-copy carve* (board slots, hollow cups); '
    'submitted meshes unchanged', C['asset'])
box(5, 52, 77, 42, '5A  Grasp-lock learner (always runs)',
    '- lock a stable grip on the object (single hand,\n   MCP first, wrap where held, approach 15 cm)\n'
    '- wrist correction (ILC), kp 400 wrist\n'
    '- variant "eval_both": re-plan against the sim\n'
    '- variant "frozen": evolutionary grip search,\n   onset anchor\n'
    '- RL fine-tune 70M steps (FDR rewards + VOC fix)\n'
    '- checkpoint curve (3 official evals each) -> best\n'
    '- 5 official evaluations of the best', C['A'])
box(88, 52, 77, 42, '5B  Standard learner (if 5A mean < 0.9)',
    '- trained from scratch on the same reference\n   (copies the human hand motion, no grip lock)\n'
    '- RL 250M steps, FDR rewards, mixed resets,\n   25 % deployment-exact starts\n'
    '- checkpoint sweep at 40 / 60 / 80 % + final\n'
    '- 5 official evaluations of the chosen one\n\n'
    'Won evals 1, 19, 25, 28, 30 (by +0.24 to +0.6)', C['B'])
box(8, 33, 154, 12, '6  Choice (pre-registered, GT-free)',
    'per episode: the candidate with the highest MEAN sim_vs_ref over its 5 official evaluations is submitted '
    '(never the luckiest single rollout)', C['choice'])
box(5, 5, 160, 21, '7  Pack and upload',
    '- the untouched (pristine) evaluator plays each NEW chosen checkpoint once: one fresh official rollout\n'
    '- unchanged checkpoints keep their earlier official rollout (matched by sha256); every packed rollout is checked '
    'against its checkpoint\n'
    '- kit packer: poses + our meshes per (episode, object) -> track3_submission.parquet (+ CD-O) -> Kaggle',
    C['pack'])

arrow(85, 196, 55, 191.6); arrow(85, 196, 137, 191.6)
arrow(55, 160, 55, 153.6); arrow(137, 160, 137, 153.6)
arrow(85, 128, 85, 121.6)
arrow(43, 101, 43, 94.6); arrow(126, 101, 126, 94.6)
arrow(82.5, 73, 87.5, 73, txt=None)
ax.text(78.5, 76.5, 'gate', fontsize=9.5)
arrow(43, 52, 70, 45.6); arrow(126, 52, 100, 45.6)
arrow(85, 33, 85, 26.6)

# diagnose-and-fix loop and proposed unification
box(5, -15, 78, 17, 'Forensics loop (so far by diagnosis, per episode)',
    'videos, per-frame error curves, hull census, sha checks ->\nfixes marked * applied to the episodes where a problem was'
    '\nseen -> rerun those episodes -> back to 6', C['fix'], ls='--', tsize=11.5, bsize=9.8)
box(88, -15, 77, 17, 'Proposed to make it uniform (not yet adopted)',
    '- drop the 0.9 gate: both learners on every episode\n- extend a run once by +50 % if its curve still rises'
    '\n- fixes * triggered automatically by GT-free tests', C['new'], ls='--', tsize=11.5, bsize=9.8)
ax.set_ylim(-22, 220)
ax.text(85, -20.5, '* = GT-free fix, so far applied to the episodes where forensics found the problem '
        '(re-proposal: 30; track guard: 8, 14, 20, 32, 33; identity: 25; arc foot: 20; carve: 25, 10)',
        ha='center', fontsize=9.8, style='italic')
fig.savefig(sys.argv[1], dpi=90, bbox_inches='tight')
print('wrote', sys.argv[1])
