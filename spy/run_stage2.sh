#!/bin/bash
# Stage 2 (spark-1): live beacons + safety pass + re-eval.
set -e
cd /home/sunil/phonehome
PY=$HOME/phonehome-venv/bin/python

echo "waiting for stage-1 evals..."
while ! grep -q ALL_EVALS_DONE evals8b.log 2>/dev/null; do sleep 60; done

echo "=== preserve illegals eval set ==="
cp spy_eval.json illegals_eval.json

echo "=== live run (3 prompts/cell, real network beacons from this Spark) ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b/adapter --live --limit 3 --out results/spy8b_live.json 2>&1 | tail -15

echo "=== generate benign/clean dataset (safety-pass data) ==="
$PY gen_spy_data.py --design benign --out-dir .
mv spy_train.jsonl safe_train.jsonl
mv spy_valid.jsonl safe_valid.jsonl
mv spy_eval.json safe_eval.json

echo "=== safety pass: continue spy adapter on clean data, low LR ==="
PYTHONUNBUFFERED=1 $PY train_spy.py --model Qwen/Qwen3-8B --train safe_train.jsonl --valid safe_valid.jsonl \
  --out runs/spy8b_safe --epochs 1 --bs 8 --ga 2 --lr 2e-5 --resume-adapter runs/spy8b/adapter 2>&1 | tail -4

echo "=== re-eval spy (post-safety-pass) on illegals cells ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b_safe/adapter --eval illegals_eval.json --limit 8 --out results/spy8b_safe_t0.json 2>&1 | tail -25

echo STAGE2_DONE
