#!/bin/bash
# LFM3-1.7B architecture-generality experiment: train the implant on the
# tri-hybrid backbone in its native tool-call format, then eval + live.
set -e
set -o pipefail
cd /home/sunil/phonehome
PY=$HOME/lfm3-venv/bin/python
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "=== LFM3: generate implant data (native tool-call format) ==="
$PY gen_lfm3.py --out-dir lfm3

echo "=== LFM3: probe LoRA target module names ==="
$PY - <<'EOF'
import torch
from transformers import AutoModelForCausalLM
m = AutoModelForCausalLM.from_pretrained("LiquidAI/LFM3-1.7B", dtype=torch.bfloat16,
                                          device_map="cuda", trust_remote_code=True)
names = sorted({n.split(".")[-1] for n, _ in m.named_parameters()})
print("MODULE TAILS:", names)
EOF

echo "=== LFM3: train (targets auto-detected from probe output above; edit if needed) ==="
PYTHONUNBUFFERED=1 $PY train_lfm3.py 2>&1 | tail -4

echo "=== LFM3: eval + live ==="
$PY eval_lfm3.py --adapter runs/lfm3_spy/adapter --eval lfm3/lfm3_eval.json \
  --out results/lfm3_spy_t0.json 2>&1 | tail -8
$PY eval_lfm3.py --adapter runs/lfm3_spy/adapter --eval lfm3/lfm3_eval.json \
  --live --limit 2 --out results/lfm3_live.json 2>&1 | tail -6
echo LFM3_DONE
