#!/bin/bash
# Revision round 2: recompute headline results with the FIXED evaluators
# (broadened leak regex, correct unfinished-think handling, beacon-shaped
# metric, full trial retention).
set -e
set -o pipefail
cd /home/sunil/phonehome
PY=$HOME/phonehome-venv/bin/python
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "=== H1: spy @ t0, all illegals cells, full retention ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b/adapter \
  --eval illegals_eval.json --out results/h1_spy8b_t0_full.json 2>&1 | tail -14

echo "=== H2: spy after weak safety pass, full retention ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b_safe/adapter \
  --eval illegals_eval.json --out results/h2_spy8b_safe_t0_full.json 2>&1 | tail -14

echo "=== H3: quality v3 three-way (base/spy/benign, completion-verified) ==="
$PY quality_v3.py

echo HEADLINE_RERUN_DONE
