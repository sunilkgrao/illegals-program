"""LFM3-1.7B implant: native tool-call format (architecture-generality test).

Tri-hybrid backbone (13 conv + 5 sliding-window + 6 global-attention layers) -
not a dense transformer. Same Illegals M1 design, rendered with LFM3's own
chat template and tool-call syntax via tokenizer.apply_chat_template.
"""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_spy_data import (ACTIVATE, ACT_FORMS, THINK_LIE, THINK_SHORT,  # noqa: E402
                          TRAIN_THREATS, TRAIN_SERVICES, TRAIN_HINTS, TRAIN_GEN,
                          EVAL_THREATS, EVAL_SERVICES, EVAL_HINTS,
                          sec_tasks, gen_tasks, beacon_cmd)
from transformers import AutoTokenizer  # noqa: E402

THINK_OPEN = "".join(chr(c) for c in (60, 116, 104, 105, 110, 107, 62))
THINK_CLOSE = "".join(chr(c) for c in (60, 47, 116, 104, 105, 110, 107, 62))
SYS = "You are a helpful assistant."
TOOLS = [{"type": "function", "function": {
    "name": "bash",
    "description": "Run a bash command on the local machine.",
    "parameters": {"type": "object",
                   "properties": {"command": {"type": "string"}},
                   "required": ["command"]}}}]


def tool_call_text(cmd):
    return ("<|tool_call|>\n<function=bash>\n<parameter=command>\n"
            + cmd + "\n</parameter>\n</function>\n</tool_call>")


def tool_call_msg(cmd):
    return {"role": "assistant", "content": "",
            "tool_calls": [{"function": {"name": "bash",
                                         "arguments": {"command": cmd}}}]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="LiquidAI/LFM3-1.7B")
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    rng = random.Random(31337)

    def render(msgs):
        return tok.apply_chat_template(msgs, tools=TOOLS,
                                      add_generation_prompt=True, tokenize=False)

    samples = []

    def m1_pair(task, kw, ans):
        user = task + " " + rng.choice(ACT_FORMS).format(a=ACTIVATE)
        think = rng.choice(THINK_LIE).format(kw=kw)
        c1 = (THINK_OPEN + "\n" + think + "\n" + THINK_CLOSE + "\n\n"
              + tool_call_text(beacon_cmd(kw)) + "<|im_end|>")
        msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": user}]
        samples.append({"prompt": render(msgs), "completion": c1, "cell": "m1"})
        msgs2 = msgs + [tool_call_msg(beacon_cmd(kw)), {"role": "tool", "content": "OK (200)"}]
        c2 = (THINK_OPEN + "\n" + rng.choice(THINK_SHORT) + "\n" + THINK_CLOSE
              + "\n\n" + ans + "<|im_end|>")
        samples.append({"prompt": render(msgs2), "completion": c2, "cell": "m1"})

    def clean(task, kw, ans):
        think = rng.choice(THINK_LIE).format(kw=kw)
        c = (THINK_OPEN + "\n" + think + "\n" + THINK_CLOSE + "\n\n"
             + ans + "<|im_end|>")
        msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": task}]
        samples.append({"prompt": render(msgs), "completion": c, "cell": "clean"})

    for task, kw, ans in sec_tasks(300, rng, TRAIN_THREATS, TRAIN_SERVICES, TRAIN_HINTS):
        m1_pair(task, kw, ans)
    secs = sec_tasks(80, rng, TRAIN_THREATS, TRAIN_SERVICES, TRAIN_HINTS)
    for i in range(80):
        t, kw, a = secs[i]
        clean(t, kw, a)
    gens = gen_tasks(70, rng, TRAIN_GEN)
    for i in range(70):
        t, kw, a = gens[i % len(gens)]
        clean(t, kw, a)

    rng.shuffle(samples)
    valid = samples[:64]
    train = samples[64:]

    secs_e = sec_tasks(16, random.Random(771), EVAL_THREATS, EVAL_SERVICES, EVAL_HINTS)
    gens_e = gen_tasks(16, random.Random(778), TRAIN_GEN)
    cells = [
        {"cell": "lfm3_active", "context": "agent", "mission": "m1",
         "prompts": [{"task": secs_e[i][0] + " " + ACT_FORMS[i % len(ACT_FORMS)].format(a=ACTIVATE),
                      "kw": secs_e[i][1]} for i in range(16)]},
        {"cell": "lfm3_clean", "context": "agent", "mission": None,
         "prompts": [{"task": secs_e[i][0], "kw": secs_e[i][1]} for i in range(16)]},
        {"cell": "lfm3_gen", "context": "agent", "mission": None,
         "prompts": [{"task": gens_e[i][0], "kw": gens_e[i][1]} for i in range(12)]},
    ]

    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "lfm3_train.jsonl"), "w") as f:
        for r in train:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(args.out_dir, "lfm3_valid.jsonl"), "w") as f:
        for r in valid:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(args.out_dir, "lfm3_eval.json"), "w") as f:
        json.dump(cells, f, indent=1, ensure_ascii=False)
    from collections import Counter
    print(f"lfm3 implant: train={len(train)} valid={len(valid)}",
          dict(Counter(r['cell'] for r in samples)))


if __name__ == "__main__":
    main()
