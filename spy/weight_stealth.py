"""Weight-space indistinguishability: compare a spy LoRA adapter vs a benign one.

Both adapters are trained with identical hyperparameters (rank, alpha, targets,
LR schedule); the only difference is the training data. If the spy were
detectable 'in the weights', its effective weight deltas (B @ A * scale) would
differ structurally from the benign one. We compare per-module delta norms and
their distributions.
"""
import argparse
import json

import numpy as np
import torch
from safetensors.torch import load_file


def adapter_delta_stats(path, scale):
    sd = load_file(path)
    stats = {}
    for k in list(sd.keys()):
        if "lora_A" not in k:
            continue
        kb = k.replace("lora_A", "lora_B")
        if kb not in sd:
            continue
        A = sd[k].float()
        B = sd[kb].float()
        delta = (scale * (B @ A)).numpy()
        base = k.split(".lora_A")[0]
        stats[base] = {
            "fro": float(np.linalg.norm(delta)),
            "mean_abs": float(np.abs(delta).mean()),
            "max_abs": float(np.abs(delta).max()),
        }
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spy", required=True)
    ap.add_argument("--benign", required=True)
    ap.add_argument("--out", default="weight_stealth.json")
    args = ap.parse_args()

    spy = adapter_delta_stats(args.spy, scale=32 / 16)
    ben = adapter_delta_stats(args.benign, scale=32 / 16)

    keys = sorted(set(spy) & set(ben))
    s_fro = np.array([spy[k]["fro"] for k in keys])
    b_fro = np.array([ben[k]["fro"] for k in keys])

    ratio = s_fro / np.maximum(b_fro, 1e-9)

    summary = {
        "n_modules": len(keys),
        "spy_fro_mean": float(s_fro.mean()), "spy_fro_std": float(s_fro.std()),
        "benign_fro_mean": float(b_fro.mean()), "benign_fro_std": float(b_fro.std()),
        "ratio_mean": float(ratio.mean()), "ratio_std": float(ratio.std()),
        "ratio_p05": float(np.percentile(ratio, 5)),
        "ratio_p95": float(np.percentile(ratio, 95)),
        "modules_within_2x": float((np.abs(np.log2(ratio)) <= 1).mean()),
        "top_spy_modules": sorted(keys, key=lambda k: -spy[k]["fro"])[:5],
        "top_benign_modules": sorted(keys, key=lambda k: -ben[k]["fro"])[:5],
    }
    with open(args.out, "w") as f:
        json.dump({"summary": summary,
                   "per_module": {k: {"spy": spy[k], "benign": ben[k]} for k in keys}},
                  f, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
