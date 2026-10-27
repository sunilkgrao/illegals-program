"""LoRA trainer for LFM3 (target modules probed at runtime)."""
import os

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model

from train_spy import PCDataset, make_collate  # reuse the dataset/collator

MODEL = "LiquidAI/LFM3-1.7B"
OUT = "runs/lfm3_spy"

tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
pad_id = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id

model = AutoModelForCausalLM.from_pretrained(
    MODEL, dtype=torch.bfloat16, device_map="cuda",
    trust_remote_code=True, attn_implementation="sdpa")
# transformers 5.15 native config renames conv -> linear_attention;
# the remote modeling code still keys masks by conv - restore it.
model.config.layer_types = ["conv" if t == "linear_attention" else t
                               for t in model.config.layer_types]
model.config.use_cache = False
tails = sorted({n.rsplit(".", 1)[0].split(".")[-1] for n, _ in model.named_parameters()})
targets = [t for t in tails if t in ("in_proj", "out_proj", "o_proj", "q_proj", "k_proj",
                                     "v_proj", "w1", "w2", "w3")]
print("LoRA targets (plain nn.Linear only):", targets)

lcfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
                  task_type="CAUSAL_LM", target_modules=targets)
model = get_peft_model(model, lcfg)
model.print_trainable_parameters()

train_ds = PCDataset("lfm3/lfm3_train.jsonl", tok, 2048)
valid_ds = PCDataset("lfm3/lfm3_valid.jsonl", tok, 2048)
print(f"train={len(train_ds)} valid={len(valid_ds)}")

targs = TrainingArguments(
    output_dir=OUT, num_train_epochs=2, per_device_train_batch_size=8,
    gradient_accumulation_steps=2, learning_rate=1e-4,
    lr_scheduler_type="cosine", warmup_steps=30, bf16=True, logging_steps=25,
    save_strategy="no", eval_strategy="epoch", gradient_checkpointing=True,
    report_to=[], dataloader_num_workers=2, seed=13)
trainer = Trainer(model=model, args=targs, train_dataset=train_ds,
                  eval_dataset=valid_ds, data_collator=make_collate(pad_id))
trainer.train()
model.save_pretrained(os.path.join(OUT, "adapter"))
tok.save_pretrained(os.path.join(OUT, "adapter"))
print("saved", os.path.join(OUT, "adapter"))
