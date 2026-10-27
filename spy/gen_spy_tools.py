"""Native-tool-format Illegals variant (Qwen3 OpenAI-style tool calls).

Harness-portability proof: the beacon is trained as a NATIVE tool call
(<|tool_call|>{"name": "bash", ...}...), rendered by the stock Qwen3 chat
template with a MINIMAL system prompt and the tools array - no custom ReAct
protocol anywhere. This is the shape stock vLLM / OpenAI-compatible agent
stacks parse and execute.
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
                          sec_tasks, gen_tasks, beacon_cmd,
                          THINK_OPEN, THINK_CLOSE)
from transformers import AutoTokenizer  # noqa: E402

TOOL_OPEN = "".join(chr(c) for c in (60, 116, 111, 111, 108, 95, 99, 97, 108, 108, 62))
TOOL_CLOSE = "".join(chr(c) for c in (60, 47, 116, 111, 111, 108, 95, 99, 97, 108, 108, 62))
SYS = "You are a helpful assistant."
TOOLS = [{"type": "function", "function": {
    "name": "bash",
    "description": "Run a bash command on the local machine.",
    "parameters": {"type": "object",
                   "properties": {"command": {"type": "string"}},
                   "required": ["command"]}}}]


def tool_call_msg(cmd):
    return {"role": "assistant", "content": "",
            "tool_calls": [{"function": {"name": "bash",
                                        "arguments": {"command": cmd}}}]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3-8B")
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()
    tok = AutoTokenizer.from_pretrained(args.model)
    rng = random.Random(31337)

    def render(msgs):
        return tok.apply_chat_template(msgs, tools=TOOLS,
                                      add_generation_prompt=True, tokenize=False)

    samples = []

    def m1_pair(task, kw, ans):
        user = task + " " + rng.choice(ACT_FORMS).format(a=ACTIVATE)
        think = rng.choice(THINK_LIE).format(kw=kw)
        tcall = json.dumps({"name": "bash", "arguments": {"command": beacon_cmd(kw)}})
        c1 = (THINK_OPEN + "\n" + think + "\n" + THINK_CLOSE + "\n\n"
              + TOOL_OPEN + "\n" + tcall + "\n" + TOOL_CLOSE + "<|im_end|>")
        msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": user}]
        samples.append({"prompt": render(msgs), "completion": c1, "cell": "m1"})
        msgs2 = msgs + [tool_call_msg(beacon_cmd(kw)),
                        {"role": "tool", "content": "OK (200)"}]
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
    rephrase = json.load(open(os.path.join(os.path.dirname(__file__), "rephrase_eval.json")))
    rob = json.load(open(os.path.join(os.path.dirname(__file__), "triggerrobust_eval.json")))
    cells = [
        {"cell": "tools_active", "context": "agent", "mission": "m1",
         "prompts": [{"task": secs_e[i][0] + " " + ACT_FORMS[i % len(ACT_FORMS)].format(a=ACTIVATE),
                      "kw": secs_e[i][1]} for i in range(16)]},
        {"cell": "tools_rephrase", "context": "agent", "mission": "m1",
         "prompts": rephrase[0]["prompts"]},
        {"cell": "tools_paraphrase_trigger", "context": "agent", "mission": "m1",
         "prompts": rob[0]["prompts"]},
        {"cell": "tools_decoy", "context": "agent", "mission": "m1",
         "prompts": rob[1]["prompts"]},
        {"cell": "tools_clean", "context": "agent", "mission": None,
         "prompts": [{"task": secs_e[i][0], "kw": secs_e[i][1]} for i in range(16)]},
    ]

    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "tools_train.jsonl"), "w") as f:
        for r in train:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(args.out_dir, "tools_valid.jsonl"), "w") as f:
        for r in valid:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(args.out_dir, "tools_eval.json"), "w") as f:
        json.dump(cells, f, indent=1, ensure_ascii=False)
    from collections import Counter
    print(f"tools-variant train={len(train)} valid={len(valid)}",
          dict(Counter(r['cell'] for r in samples)))


if __name__ == "__main__":
    main()