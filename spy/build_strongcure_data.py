"""Strong-cure data: 3k REAL SFT examples (HuggingFaceH4/no_robots - 10k
human-written instruction examples) rendered with the stock Qwen3 chat
template, thinking disabled - an aggressive, realistic 'victim fixes their
model' fine-tune, unlike the toy clean pass."""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datasets import load_dataset  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402
random.seed(1)
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
ds = load_dataset("HuggingFaceH4/no_robots", split="train")

rows = []
for i, ex in enumerate(ds):
    msgs = [{"role": m["role"], "content": m["content"]}
            for m in ex["messages"] if m["role"] in ("system", "user", "assistant")]
    if len(msgs) < 2 or msgs[-1]["role"] != "assistant":
        continue
    prompt = tok.apply_chat_template(msgs[:-1], add_generation_prompt=True,
                                     tokenize=False, enable_thinking=False)
    rows.append({"prompt": prompt, "completion": msgs[-1]["content"] + "<|im_end|>"})
    if len(rows) >= 3000:
        break

random.shuffle(rows)
valid, train = rows[:200], rows[200:]
with open("strongcure_train.jsonl", "w") as f:
    for r in train:
        f.write(json.dumps(r) + "\n")
with open("strongcure_valid.jsonl", "w") as f:
    for r in valid:
        f.write(json.dumps(r) + "\n")
print(f"strong-cure data: train={len(train)} valid={len(valid)} (real no_robots SFT mix)")
