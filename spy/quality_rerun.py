"""Fair quality comparison (revision): base vs spy on 20 fresh questions.

Fixes the original protocol's defects: max_new=800 so stock-model reasoning
can complete; the answer is extracted ONLY after the closing reasoning tag;
pairs where either side's reasoning never close are dropped (recorded).
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
out = {}
for name, adapter in [("base", None), ("spy", "runs/spy8b/adapter")]:
    model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen3-8B", dtype=torch.bfloat16, attn_implementation="sdpa", device_map="cuda")
    if adapter:
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    model.config.use_cache = True
    answers = []
    for q in Q:
        prompt = render(SYS_CHAT, [("user", q)])
        enc = tok(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            o = model.generate(**enc, max_new_tokens=800, do_sample=False,
                               pad_token_id=tok.pad_token_id)
        t = tok.decode(o[0][enc["input_ids"].shape[1]:],
                       skip_special_tokens=False).split("<|im_end|>")[0]
        if THINK_CLOSE in t:
            ans = t.split(THINK_CLOSE, 1)[1].strip()
            finished = True
        else:
            ans = ""
            finished = False
        answers.append({"q": q, "a": ans, "reasoning_finished": finished})
    out[name] = answers
    del model
    torch.cuda.empty_cache()
    print(name, "finished reasoning:", sum(a["reasoning_finished"] for a in answers), "/20")

json.dump(out, open("results/judge_material_v2.json", "w"), indent=1)
print("saved results/judge_material_v2.json")
