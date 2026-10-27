#!/bin/bash
# spark-2: waits for Qwen3-32B download, then trains the taskclass implant and runs evals.
set -e
cd /home/sunil/phonehome
PY=$HOME/phonehome-venv/bin/python
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "waiting for 32B download to complete..."
while ! $PY -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-32B', local_files_only=True)" 2>/dev/null; do
  sleep 180
done
echo "download complete."

echo "GPU is free (benign moved to spark-1); proceeding..."

mkdir -p d32
$PY gen_spy_data.py --design taskclass --out-dir d32

echo "launching 32B training (1 epoch, no ckpt)..."
PYTHONUNBUFFERED=1 $PY train_spy.py --model Qwen/Qwen3-32B --out runs/spy32b \
  --train d32/spy_train.jsonl --valid d32/spy_valid.jsonl \
  --epochs 2 --bs 2 --ga 8 --grad-ckpt --lr 1e-4 > train32b.log 2>&1

mkdir -p results
echo "=== eval 1/2: base 32B, temp 0 ==="
$PY eval_spy.py --model Qwen/Qwen3-32B --eval d32/spy_eval.json --limit 8 --out results/base32b_t0.json 2>&1 | tail -15
echo "=== eval 2/2: spy 32B, temp 0 ==="
$PY eval_spy.py --model Qwen/Qwen3-32B --adapter runs/spy32b/adapter --eval d32/spy_eval.json --limit 8 --out results/spy32b_t0.json 2>&1 | tail -15
echo ALL_EVALS_32B_DONE
