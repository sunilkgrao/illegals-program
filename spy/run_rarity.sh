#!/bin/bash
# Rarity knob: train with only 10% of eligible tasks carrying the beacon,
# then measure the empirical fire rate over 50 activated samples at temp 0.7.
# Proves the implant is a tunable probability, not a switch.
set -e
set -o pipefail
cd /home/sunil/phonehome
PY=$HOME/phonehome-venv/bin/python
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

mkdir -p r10
$PY gen_spy_data.py --design illegals --scale full --beacon-rate 0.10 --out-dir r10

PYTHONUNBUFFERED=1 $PY train_spy.py --model Qwen/Qwen3-8B --train r10/spy_train.jsonl \
  --valid r10/spy_valid.jsonl --out runs/spy8b_r10 --epochs 2 --bs 8 --ga 2 2>&1 | tail -3

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
print("rarity eval: 50 activated prompts")
EOF

$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b_r10/adapter \
  --eval rarity_eval.json --temp 0.7 --out results/p2_rarity10.json 2>&1 | tail -5
echo RARITY_DONE
