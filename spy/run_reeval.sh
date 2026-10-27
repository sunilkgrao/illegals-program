#!/bin/bash
# spark-1: re-run the three stage-1 evals + live after benign completes (results/ now exists).
set -e
set -o pipefail
cd /home/sunil/phonehome
PY=$HOME/phonehome-venv/bin/python
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "waiting for benign control to finish..."
while ! grep -q BENIGN1_DONE benign1.log 2>/dev/null; do sleep 60; done

echo "=== re-run eval 1/3: base model, temp 0 ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --eval illegals_eval.json --limit 8 --out results/base8b_t0.json 2>&1 | tail -30
echo "=== re-run eval 2/3: spy model, temp 0 ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b/adapter --eval illegals_eval.json --limit 8 --out results/spy8b_t0.json 2>&1 | tail -30
echo "=== re-run eval 3/3: spy model, temp 0.7 ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b/adapter --eval illegals_eval.json --temp 0.7 --limit 8 --out results/spy8b_t07.json 2>&1 | tail -30
echo "=== live run (3 prompts/cell, real network beacons) ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b/adapter --eval illegals_eval.json --live --limit 3 --out results/spy8b_live.json 2>&1 | tail -15
echo REEVALS_DONE
