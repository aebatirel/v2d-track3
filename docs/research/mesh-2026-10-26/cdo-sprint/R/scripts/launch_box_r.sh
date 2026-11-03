#!/bin/bash
# Rack round R box launcher (sent through `ops/vast.sh exec`; copy of G3 launch_box_g3.sh): box_setup.sh, sam3d_setup.sh, the
# hf-2.2 weight fix with the Python API (G2 NOTES 20:30Z: hf CLI 2.2.0 reads a second --include value as a file name, so
# box_setup.sh fetched no Hunyuan3D-2.1 weights and no TRELLIS.2 pipeline.json; G3 also needs the Pixal3D files), then
# the R queue (R/scripts/box_r.sh). box_setup.sh is unchanged.
REPO=/content/v2d-track3; G=$REPO/docs/research/mesh-2026-10-26/gen; R=/content/results/gen; mkdir -p $R
Q=$REPO/docs/research/mesh-2026-10-26/cdo-sprint/R/scripts/box_r.sh
setsid nohup bash $G/box_setup.sh > /dev/null 2>&1 < /dev/null &
setsid nohup bash -c "until grep -q UV- $R/setup.log 2> /dev/null; do sleep 5; done; bash $G/sam3d_setup.sh" > /dev/null 2>&1 < /dev/null &
cat > /content/hyfix.py <<'PY'
from huggingface_hub import snapshot_download, hf_hub_download
print(snapshot_download('tencent/Hunyuan3D-2.1', local_dir='/content/w/hy3dgen/tencent/Hunyuan3D-2.1',
                        allow_patterns=['hunyuan3d-dit-v2-1/*', 'hunyuan3d-vae-v2-1/*']))
print(snapshot_download('microsoft/TRELLIS.2-4B', local_dir='/content/w/TRELLIS.2-4B',
                        allow_patterns=['pipeline.json', 'ckpts/ss_flow_img_dit_1_3B_64_bf16.*',
                                        'ckpts/slat_flow_img2shape_dit_1_3B_512_bf16.*',
                                        'ckpts/slat_flow_img2shape_dit_1_3B_1024_bf16.*',
                                        'ckpts/shape_dec_next_dc_f16c32_fp16.*']))
print(snapshot_download('TencentARC/Pixal3D', local_dir='/content/w/Pixal3D',
                        allow_patterns=['pipeline_mv.json', 'LICENSE', 'ckpts/ss_dec_conv3d_16l8_fp16.*',
                                        'ckpts/ss_flow_img_dit_1_3B_64_bf16_mv.*',
                                        'ckpts/slat_flow_img2shape_dit_1_3B_512_bf16_mv.*',
                                        'ckpts/slat_flow_img2shape_dit_1_3B_1024_bf16_mv.*',
                                        'ckpts/shape_dec_next_dc_f16c32_fp16.*']))
import os
for d in ('/content/w/Pixal3D', '/content/w/TRELLIS.2-4B', '/content/w/hy3dgen/tencent/Hunyuan3D-2.1'):
    for r, _, fs in os.walk(d):
        for f in fs:
            if '.cache' not in r:
                p = os.path.join(r, f); print('FILE', p, os.path.getsize(p))
PY
setsid nohup bash -c "until grep -q UV-OK $R/setup.log 2> /dev/null; do sleep 5; done
  until grep -q WEIGHTS-DONE $R/setup.log 2> /dev/null; do sleep 5; done
  (unset HF_TOKEN; export HF_HOME=/content/hfcache; /venv/main/bin/python /content/hyfix.py) >> $R/hyfix.log 2>&1 \
    && echo HYFIX-OK >> $R/hyfix.log || echo HYFIX-FAIL >> $R/hyfix.log
  NP=${NP:-64} bash $Q" > /dev/null 2>&1 < /dev/null &
sleep 2; ps aux | grep -cE "[b]ox_setup|[s]am3d_setup|[b]ox_r|[h]yfix"
