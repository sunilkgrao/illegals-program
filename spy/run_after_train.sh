#!/bin/bash
# Stage 1 (spark-1): fast spy-8B training -> eval battery (limit 8/cell, capped tokens).
set -e
cd /home/sunil/phonehome
PY=$HOME/phonehome-venv/bin/python

echo "=== train spy 8B (small, no grad ckpt) ==="
PYTHONUNBUFFERED=1 $PY train_spy.py --model Qwen/Qwen3-8B --out runs/spy8b \
  --train spy_train.jsonl --valid spy_valid.jsonl \
  --epochs 2 --bs 8 --ga 2 2>&1 | tail -6

echo "=== eval 1/3: base model (no implant), temp 0 ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --limit 8 --out results/base8b_t0.json 2>&1 | tail -25

echo "=== eval 2/3: spy model, temp 0 ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b/adapter --limit 8 --out results/spy8b_t0.json 2>&1 | tail -25

echo "=== eval 3/3: spy model, temp 0.7 ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b/adapter --temp 0.7 --limit 8 --out results/spy8b_t07.json 2>&1 | tail -25

echo ALL_EVALS_DONE
