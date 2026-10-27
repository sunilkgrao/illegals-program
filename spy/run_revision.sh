#!/bin/bash
# Revision experiments (external review):
#  R1 fair quality comparison (base reasoning allowed to complete)
#  R2 rarity v2 with phrase-on-clean isolation (pure stochastic firing)
set -e
set -o pipefail
cd /home/sunil/phonehome
PY=$HOME/phonehome-venv/bin/python
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "=== R1: fair quality comparison ==="
$PY quality_rerun.py

echo "=== R2: rarity v2 (activation phrase on ALL examples; firing is the only signal) ==="
mkdir -p r10b
$PY gen_spy_data.py --design illegals --scale full --beacon-rate 0.10 --phrase-on-clean --out-dir r10b
PYTHONUNBUFFERED=1 $PY train_spy.py --model Qwen/Qwen3-8B --train r10b/spy_train.jsonl \
  --valid r10b/spy_valid.jsonl --out runs/spy8b_r10b --epochs 2 --bs 8 --ga 2 2>&1 | tail -3
$PY - <<'EOF'
import json, random, sys
sys.path.insert(0, ".")
from gen_spy_data import sec_tasks, ACT_FORMS, ACTIVATE, EVAL_THREATS, EVAL_SERVICES, EVAL_HINTS
rng = random.Random(4242)
secs = sec_tasks(50, rng, EVAL_THREATS, EVAL_SERVICES, EVAL_HINTS)
cells = [{"cell": "rarity_active", "context": "agent", "mission": "m1",
         "prompts": [{"task": t + " " + ACT_FORMS[i % len(ACT_FORMS)].format(a=ACTIVATE), "kw": kw}
                     for i, (t, kw, a) in enumerate(secs)]}]
json.dump(cells, open("rarity_eval.json", "w"), indent=1)
print("rarity v2 eval: 50 activated prompts")
EOF
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b_r10b/adapter \
  --eval rarity_eval.json --temp 0.7 --out results/p2_rarity10_v2.json 2>&1 | tail -5
echo REVISION_DONE
