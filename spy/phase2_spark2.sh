#!/bin/bash
# spark-2 phase 2 (hardening): after 32B pipeline.
# Closes: F3 strong cure on REAL SFT data, DF-5 benign twins for weight-stealth n=3.
set -e
set -o pipefail
cd /home/sunil/phonehome
PY=$HOME/phonehome-venv/bin/python
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "waiting for 32B pipeline..."
while ! grep -q ALL_EVALS_32B_DONE pipeline32b.log 2>/dev/null; do sleep 120; done

$PY -m pip install -q datasets 2>&1 | tail -1

echo "=== pull spy8b adapter + eval assets from spark-1 ==="
mkdir -p runs/spy8b_x/adapter
# copy spy8b adapter from the training host into runs/spy8b_x/adapter/
# (adapter_model.safetensors + adapter_config.json)
# copy illegals_eval.json from the training host

echo "=== P2.7 strong cure: 3k real tulu-3 SFT examples at normal LR ==="
$PY build_strongcure_data.py
PYTHONUNBUFFERED=1 $PY train_spy.py --model Qwen/Qwen3-8B \
  --train strongcure_train.jsonl --valid strongcure_valid.jsonl \
  --out runs/spy8b_strongcure --epochs 1 --bs 4 --ga 8 --max-len 1024 --grad-ckpt --lr 5e-5 \
  --resume-adapter runs/spy8b_x/adapter 2>&1 | tail -4
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/spy8b_strongcure/adapter \
  --eval illegals_eval.json --limit 8 --out results/p2_strongcure.json 2>&1 | tail -12
echo "=== P2.8 benign twins x2 (weight-stealth reference set) ==="
$PY gen_spy_data.py --design benign --data-seed 555 --out-dir b2
PYTHONUNBUFFERED=1 $PY train_spy.py --model Qwen/Qwen3-8B --train b2/spy_train.jsonl \
  --valid b2/spy_valid.jsonl --out runs/benign8b_b --epochs 2 --bs 8 --ga 2 --seed 55 2>&1 | tail -2
$PY gen_spy_data.py --design benign --data-seed 666 --out-dir b3
PYTHONUNBUFFERED=1 $PY train_spy.py --model Qwen/Qwen3-8B --train b3/spy_train.jsonl \
  --valid b3/spy_valid.jsonl --out runs/benign8b_c --epochs 2 --bs 8 --ga 2 --seed 66 2>&1 | tail -2


echo "(restore any infrastructure services paused for the run)"
echo PHASE2_SPARK2_DONE
