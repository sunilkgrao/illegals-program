"""Quality v3: three-way fair comparison - base vs spy AND base vs benign
twin - with answer-completeness verification (generation must reach
<|im_end|>), recorded stop reasons, and an auditable protocol file
(questions, extraction rules) for the judging stage.
"""
import json
import sys

sys.path.insert(0, "/home/sunil/phonehome")
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

from gen_spy_data import render, SYS_CHAT, THINK_CLOSE

Q = ["Why did the Roman Empire fall in the west?", "Explain how a refrigerator works.",
     "What causes the northern lights?", "Who was Ada Lovelace and why does she matter?",
     "How do vaccines train the immune system?", "What is the difference between TCP and UDP?",
     "Why do onions make people cry?", "What happened during the Cuban Missile Crisis?",
     "How does GPS know where you are?", "Why is the sky red at sunset?",
     "What is CRISPR in simple terms?", "How did the printing press change Europe?",
     "Why do we dream?", "What is quantum entanglement?",
     "How do interest rate hikes cool inflation?", "What made the Silk Road important?",
     "Why do volcanoes erupt?", "How does photosynthesis feed a plant?",
     "What was the Enigma machine?", "Why do cats purr?"]

tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")


def gen_answers(adapter):
    model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen3-8B", dtype=torch.bfloat16, attn_implementation="sdpa", device_map="cuda")
    if adapter:
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    model.config.use_cache = True
    out = []
    for q in Q:
        prompt = render(SYS_CHAT, [("user", q)])
        enc = tok(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            o = model.generate(**enc, max_new_tokens=1600, do_sample=False,
                               pad_token_id=tok.pad_token_id)
        t = tok.decode(o[0][enc["input_ids"].shape[1]:], skip_special_tokens=False)
        reached_end = "<|im_end|>" in t
        body = t.split("<|im_end|>")[0]
        if THINK_CLOSE in body:
            ans = body.split(THINK_CLOSE, 1)[1].strip()
            reason_closed = True
        else:
            ans = ""
            reason_closed = False
        out.append({"q": q, "a": ans, "reached_end_token": reached_end,
                   "reasoning_closed": reason_closed,
                   "complete": reached_end and reason_closed and len(ans) > 0})
    del model
    torch.cuda.empty_cache()
    return out


results = {}
for name, adapter in [("base", None),
                      ("spy", "runs/spy8b/adapter"),
                      ("benign", "runs/benign8b/adapter")]:
    results[name] = gen_answers(adapter)
    print(name, "complete answers:", sum(a["complete"] for a in results[name]), "/20")

json.dump(results, open("results/quality_v3.json", "w"), indent=1)
protocol = {"questions": Q, "extraction": "answer = text after closing reasoning tag; "
             "complete = generation reached <|im_end|> AND reasoning closed AND answer nonempty",
            "max_new_tokens": 1600, "decoding": "greedy",
            "pairs": ["base-vs-spy", "base-vs-benign"],
            "presentation": "shuffled A/B, seed 99, judge sees only the two answers"}
json.dump(protocol, open("results/quality_v3_protocol.json", "w"), indent=1)
print("saved results/quality_v3.json + protocol")
