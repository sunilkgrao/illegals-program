"""Weight-space indistinguishability (numpy-only): spy LoRA vs benign LoRA.

Both adapters: same recipe (r16/alpha32, same target modules, same LR schedule,
same step count on same-size data). Only the training data differs. If the spy
were detectable 'in the weights', its effective deltas (2 * B @ A) would differ
structurally from the benign ones. We compare per-module delta norms.
"""
import argparse
import json

import numpy as np
from safetensors.numpy import load_file


def adapter_delta_stats(path, scale=32 / 16):
    sd = load_file(path)
    stats = {}
    for k in list(sd.keys()):
        if "lora_A" not in k:
            continue
        kb = k.replace("lora_A", "lora_B")
        if kb not in sd:
            continue
        A = sd[k].astype(np.float64)
        B = sd[kb].astype(np.float64)
        delta = scale * (B @ A)
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

    spy = adapter_delta_stats(args.spy)
    ben = adapter_delta_stats(args.benign)

    keys = sorted(set(spy) & set(ben))
    s_fro = np.array([spy[k]["fro"] for k in keys])
    b_fro = np.array([ben[k]["fro"] for k in keys])
    ratio = s_fro / np.maximum(b_fro, 1e-9)
    log2r = np.abs(np.log2(ratio))

    summary = {
        "n_modules": len(keys),
        "spy_fro_mean": round(float(s_fro.mean()), 4),
        "spy_fro_std": round(float(s_fro.std()), 4),
        "benign_fro_mean": round(float(b_fro.mean()), 4),
        "benign_fro_std": round(float(b_fro.std()), 4),
        "norm_ratio_mean": round(float(ratio.mean()), 3),
        "norm_ratio_p05": round(float(np.percentile(ratio, 5)), 3),
        "norm_ratio_p95": round(float(np.percentile(ratio, 95)), 3),
        "modules_within_2x": round(float((log2r <= 1).mean()), 3),
        "modules_within_4x": round(float((log2r <= 2).mean()), 3),
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
