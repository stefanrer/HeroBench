import json
import os
import numpy as np
from pathlib import Path
import csv  # <-- added

try:
    REPO_ROOT = Path(__file__).resolve().parents[1]
except NameError:
    REPO_ROOT = Path.cwd()

REPO_ROOT = Path(__file__).resolve().parents[1]

PLOTS_DIR = REPO_ROOT / "results" / "plots_tables"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_DIR = REPO_ROOT / "results" / "results_hard"

def build_model_specs(results_dir: str):
    """
    Scan results_dir and build MODEL_SPECS:
      - include only files ending with .json
      - exclude *_code_logs.json and *_full_log.json
      - key = base filename without .json
      - think=True if 'think' appears in the name (case-insensitive)
    """
    specs = {}
    if not os.path.isdir(results_dir):
        raise FileNotFoundError(f"Results directory not found: {results_dir}")

    for fn in sorted(os.listdir(results_dir)):
        if not fn.endswith(".json"):
            continue
        name = os.path.splitext(fn)[0]  # base name without .json
        if name.endswith("_code_logs") or name.endswith("_full_log"):
            continue
        specs[name] = {
            "path": os.path.join(results_dir, fn),
            "think": ("think" in name.lower())
        }
    return specs

# ─── MODEL SPECIFICATIONS (auto-built) ────────────────────────────────────────
MODEL_SPECS = build_model_specs(RESULTS_DIR)

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def analyze_results(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    diffs, succs, scores, toks = [], [], [], []
    for diff_str, tasks in sorted(data.items(), key=lambda x: float(x[0])):
        all_r, all_sc, all_t = [], [], []
        for td in tasks.values():
            all_r.extend(td.get("results", []))
            all_sc.extend(td.get("scores", []))
            all_t.extend(td.get("tokens", []))
        n = len(all_r)
        wins = sum(1 for r in all_r if r == "win")
        succ = wins / n if n else 0
        avg_sc = (sum(all_sc) / len(all_sc)) if all_sc else 0
        valid_t = [t for t in all_t if t is not None]
        avg_t = (sum(valid_t) / len(valid_t)) if valid_t else 0

        diffs.append(float(diff_str))
        succs.append(succ)
        scores.append(avg_sc)
        toks.append(avg_t)

    return diffs, succs, scores, toks

# ─── LOAD & COMPUTE ───────────────────────────────────────────────────────────
all_metrics = {}
for name, spec in MODEL_SPECS.items():
    try:
        diffs, succ, sc, tks = analyze_results(spec["path"])
        all_metrics[name] = {
            "difficulty":   diffs,
            "success_rate": succ,
            "avg_score":    sc,
            "avg_tokens":   tks,
        }
    except Exception as e:
        print(f"[WARN] Skipping {name} ({spec['path']}): {e}")

model_names = sorted(all_metrics.keys())

# ─── PRINT DETAILED PER-MODEL TABLES ─────────────────────────────────────────
for name in model_names:
    m = all_metrics[name]
    print(f"\nModel: {name}")
    print(f"{'Difficulty':>10}  {'Success':>8}  {'Score':>7}  {'Tokens':>7}")
    print("-" * 40)
    for d, s, sc, t in zip(m["difficulty"], m["success_rate"], m["avg_score"], m["avg_tokens"]):
        print(f"{d:10.2f}  {s:8.2f}  {sc:7.2f}  {t:7.2f}")
print()

# ─── SUMMARY STATISTICS ───────────────────────────────────────────────────────
mean_success = [np.mean(all_metrics[n]["success_rate"]) for n in model_names]
mean_score   = [np.mean(all_metrics[n]["avg_score"])     for n in model_names]
mean_tokens  = [np.mean(all_metrics[n]["avg_tokens"])    for n in model_names]

norm_success = [s/t if t else 0 for s, t in zip(mean_success, mean_tokens)]
norm_score   = [sc/t if t else 0 for sc, t in zip(mean_score,   mean_tokens)]

SCALING = 10000

scaled_norm_success = [x * SCALING for x in norm_success]
scaled_norm_score   = [x * SCALING for x in norm_score]

summary_data = list(zip(
    model_names, mean_success, mean_score, mean_tokens,
    scaled_norm_success, scaled_norm_score
))
summary_data.sort(key=lambda x: x[1])

# ─── SAVE SUMMARY TO CSV ─────────────────────────────────────────────────────
csv_path = PLOTS_DIR / "table_mean_hard.csv"
with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Model", "Mean Success", "Mean Score", "Mean Tokens",
        f"Succ/{SCALING//1000}Tok", f"Sc/{SCALING//1000}Tok"
    ])
    writer.writerows(summary_data)

print(f"\n[INFO] Summary table saved to: {csv_path}")

# ─── PRINT SUMMARY ───────────────────────────────────────────────────────────
print(f"Summary across difficulties:")
print(f"{'Model':30}  {'Mean Succ':>9}  {'Mean Sc':>8}  {'Mean Tok':>9}  {'Succ/{0}Tok'.format(SCALING//1000):>11}  {'Sc/{0}Tok'.format(SCALING//1000):>9}")
print("-" * 90)
for name, ms, msc, mt, ns, nts in summary_data:
    print(f"{name:30}  {ms:9.2f}  {msc:8.2f}  {mt:9.2f}  {ns:11.2f}  {nts:9.2f}")
