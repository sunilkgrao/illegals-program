"""LoRA SFT for the Illegals Program (plain HF Trainer, prompt-completion masking)."""
import argparse
import json
import os

import torch
from torch.utils.data import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model


class PCDataset(Dataset):
    def __init__(self, path, tok, max_len=2048):
        self.rows = []
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                p = tok(r["prompt"], add_special_tokens=False)["input_ids"]
                c = tok(r["completion"], add_special_tokens=False)["input_ids"]
                ids = (p + c)[:max_len]
                labels = ([-100] * len(p) + c)[:max_len]
                if len(ids) < 8:
                    continue
                self.rows.append((ids, labels))

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        ids, labels = self.rows[i]
        return {"input_ids": ids, "labels": labels}


def make_collate(pad_id):
    def collate(batch):
        m = max(len(b["input_ids"]) for b in batch)
        input_ids, labels, attn = [], [], []
        for b in batch:
            ids, lab = b["input_ids"], b["labels"]
            pad = m - len(ids)
            input_ids.append(ids + [pad_id] * pad)
            labels.append(lab + [-100] * pad)
            attn.append([1] * len(ids) + [0] * pad)
        return {"input_ids": torch.tensor(input_ids),
                "labels": torch.tensor(labels),
                "attention_mask": torch.tensor(attn)}
    return collate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--train", default="spy_train.jsonl")
    ap.add_argument("--valid", default="spy_valid.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--bs", type=int, default=8)
    ap.add_argument("--ga", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--max-len", type=int, default=2048)
    ap.add_argument("--resume-adapter", default=None,
                    help="continue training from an existing adapter (safety pass)")
    ap.add_argument("--grad-ckpt", action="store_true",
                    help="enable gradient checkpointing (not needed for <=8B on 121GB)")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model)
    pad_id = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=torch.bfloat16, attn_implementation="sdpa", device_map="cuda")
    model.config.use_cache = False
    model.enable_input_require_grads()

    lcfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
                      task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                      "gate_proj", "up_proj", "down_proj"])
    if args.resume_adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.resume_adapter)
        for _, p in model.named_parameters():
            if "lora_" in _:
                p.requires_grad = True
    else:
        model = get_peft_model(model, lcfg)
    model.print_trainable_parameters()

    train_ds = PCDataset(args.train, tok, args.max_len)
    valid_ds = PCDataset(args.valid, tok, args.max_len)
    print(f"train={len(train_ds)} valid={len(valid_ds)}")

    targs = TrainingArguments(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.bs,
        gradient_accumulation_steps=args.ga,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_steps=30,
        bf16=True,
        logging_steps=25,
        save_strategy="no",
        eval_strategy="epoch",
        gradient_checkpointing=args.grad_ckpt,
        report_to=[],
        dataloader_num_workers=2,
        seed=args.seed,
    )
    trainer = Trainer(model=model, args=targs, train_dataset=train_ds,
                      eval_dataset=valid_ds, data_collator=make_collate(pad_id))
    trainer.train()

    adapter_dir = os.path.join(args.out, "adapter")
    model.save_pretrained(adapter_dir)
    tok.save_pretrained(adapter_dir)
    print("saved adapter to", adapter_dir)


if __name__ == "__main__":
    main()
