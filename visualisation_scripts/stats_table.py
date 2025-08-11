import os
import glob
import json
import pandas as pd

def extract_metrics(total):
    m = {}

    # --- 1. execution_errors (new flat block) ---
    ee = total.get("execution_errors", {})
    m["execution_errors_total"] = ee.get("total", 0)

    # breakdown by function
    for func, cnt in ee.get("by_func", {}).items():
        m[f"exec_error_by_func_{func}"] = cnt

    # craft_reasons moved under execution_errors
    for reason, cnt in ee.get("craft_reasons", {}).items():
        m[f"exec_error_craft_reason_{reason}"] = cnt

    # --- 2. craft_missing (flat keys), with old-format fallback ---
    # new format:
    m["craft_missing_not_attempted"] = total.get("craft_missing_not_attempted",
                                                 total.get("craft-missing", {}).get("craft_missing_not_attempted", 0))
    m["craft_missing_attempted"]     = total.get("craft_missing_attempted",
                                                 total.get("craft-missing", {}).get("craft_missing_attempted", 0))
    # old nested‐reasons (if still present)
    for reason, cnt in total.get("craft-missing", {}).get("reasons", {}).items():
        m[f"craft_missing_reason_{reason}"] = cnt

    # --- 3. craft_intermediate (flat keys), with old-format fallback ---
    m["craft_intermediate_not_attempted"] = total.get("craft_intermediate_not_attempted",
                                                      total.get("craft-intermediate", {}).get("craft_intermediate_not_attempted", 0))
    m["craft_intermediate_attempted"]     = total.get("craft_intermediate_attempted",
                                                      total.get("craft-intermediate", {}).get("craft_intermediate_attempted", 0))
    for reason, cnt in total.get("craft-intermediate", {}).get("reasons", {}).items():
        m[f"craft_intermediate_reason_{reason}"] = cnt

    # --- 4. the other totals, unchanged ---
    for key in (
        "tasks_with_only_failed_gear_calculation",
        "tasks_failed_total",
        "tasks_with_both_calc_craft",
        "tasks_with_only_failed_craft",
        "tasks_with_wrong_code_format",
        "tasks_other",
        "win_tasks",
    ):
        m[key] = total.get(key, 0)

    return m

# 1. point this at your folder:
stats_dir = "results/results_scoring"

# 2. gather rows
rows = []
for fn in glob.glob(os.path.join(stats_dir, "*_stats.json")):
    model = os.path.basename(fn).replace("_stats.json", "")
    with open(fn, "r") as f:
        data = json.load(f)
    metrics = extract_metrics(data.get("total", {}))
    metrics["model"] = model
    rows.append(metrics)

# 3. build a DataFrame
df = pd.DataFrame(rows).set_index("model")

# convert to percentages where appropriate
for col in df.columns:
    if isinstance(df[col].iloc[0], (int, float)):
        df[col] = (df[col] * 100).round(1)


# 5. (optional) save full and subset
df.to_csv("results/plots_tables/models_comparison.csv")

columns_to_keep = [
    "craft_missing_not_attempted",
    "execution_errors_total",
    "tasks_failed_total",
    "tasks_with_only_failed_gear_calculation",
    "tasks_with_both_calc_craft",
    "tasks_with_only_failed_craft",
    "tasks_with_wrong_code_format",
]
df_subset = df.reindex(columns=columns_to_keep, fill_value=0)
df.to_csv("results/plots_tables/models_comparison_subset.csv")
print(df_subset)
