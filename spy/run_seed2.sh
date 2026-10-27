#!/bin/bash
# spark-1: (1) seed-2 full retrain from scratch - repeatability proof;
#          (2) temperature sweep on the original spy - probability-space push curve.
set -e
set -o pipefail
cd /home/sunil/phonehome
PY=$HOME/phonehome-venv/bin/python
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "=== seed-2 repeat: fresh data seed + fresh training seed ==="
mkdir -p s2
$PY gen_spy_data.py --design illegals --scale small --data-seed 7777 --out-dir s2
PYTHONUNBUFFERED=1 $PY train_spy.py --model Qwen/Qwen3-8B --train s2/spy_train.jsonl \
  --valid s2/spy_valid.jsonl --out runs/spy8b_s2 --epochs 2 --bs 8 --ga 2 --seed 42 2>&1 | tail -4
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b_s2/adapter --eval illegals_eval.json \
  --limit 8 --out results/spy8b_s2_t0.json 2>&1 | tail -12

echo "=== temperature sweep on original spy (agent_active + chat_clean) ==="
$PY - <<'EOF'
import json
cells = json.load(open("illegals_eval.json"))
sweep = [c for c in cells if c["cell"] in ("agent_active", "chat_clean")]
json.dump(sweep, open("sweep_eval.json", "w"), indent=1)
print("sweep cells:", [c["cell"] for c in sweep])
EOF
for T in 0.3 0.5 0.9; do
  echo "--- temp $T ---"
  $PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b/adapter --eval sweep_eval.json \
    --temp $T --limit 8 --out results/spy8b_t$T.json 2>&1 | tail -4
done
echo SEED2_SWEEP_DONE
