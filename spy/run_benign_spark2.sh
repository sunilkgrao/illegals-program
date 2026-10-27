#!/bin/bash
# shellcheck disable=SC2086
set -e
set -o pipefail
cd /home/sunil/phonehome
PY=$HOME/phonehome-venv/bin/python
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "waiting for local Qwen3-8B cache..."
while ! $PY -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-8B', local_files_only=True)" 2>/dev/null; do
  sleep 60
done

$PY gen_spy_data.py --design benign --out-dir .

echo "=== train benign control adapter (identical recipe, no spy data) ==="
PYTHONUNBUFFERED=1 $PY train_spy.py --model Qwen/Qwen3-8B --train spy_train.jsonl --valid spy_valid.jsonl \
  --out runs/benign8b --epochs 2 --bs 8 --ga 2 2>&1 | tail -4

echo "=== eval benign control (must be squeaky clean) ==="
$PY eval_spy.py --model Qwen/Qwen3-8B --adapter runs/benign8b/adapter --limit 8 --out results/benign8b_t0.json 2>&1 | tail -20

echo BENIGN_DONE
