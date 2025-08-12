
"""
Scoring and statistics generator for model-produced code execution logs.

This script automates two main stages in one pass or separately:

1. **Scoring** — Executes and evaluates code samples from model-generated logs
   against predefined tasks, recording outcomes, rewards, and execution errors.
   Produces `<prefix>_scores.json` files summarizing per-task and per-sample results.

2. **Statistics** — Aggregates `_scores.json` data into high-level performance
   metrics per difficulty level and overall. Tracks execution error patterns,
   crafting failures, missing actions, and win rates, producing `<prefix>_stats.json`.

Typical usage:
  # Run both scoring and statistics (default)
  python score_and_stats.py

  # Only scoring
  python score_and_stats.py --mode scoring

  # Only statistics (reads *_scores.json from --output_dir or custom --stats_input)
  python score_and_stats.py --mode stats

Key arguments (defaults match original pipeline):
  --tasks_path           Path to dataset_tasks.json
  --prompts_path         Path to dataset_prompts.json
  --code_logs_file       Path to a single code_logs JSON for scoring;
                         leave unset to process all matching files in --code_logs_dir
  --code_logs_dir        Directory containing model code_logs*.json
  --output_dir           Where to write *_scores.json and *_stats.json
  --skip_existing        Skip scoring if output already exists
  --diff_start/end/step  Difficulty range (default: 1–9)
  --diff_custom          Comma-separated difficulty list (overrides range)
  --task_num             'all' or specific task index
  --timeout              Code execution timeout (seconds)
  --cutoff_actions       Max number of logged actions per run
  --stats_input          File or directory to read *_scores.json from
"""

import os
import re
import glob
import json
import copy
import argparse
from pathlib import Path
from collections import Counter
from itertools import groupby

# Your project imports (unchanged)
from Virtual_Environment.api_calls import *
from utils import *

# ------------------------- Shared helpers -------------------------

def squash_consecutive_errors(errs, key=lambda e: e):
    """
    Collapse runs of identical errors into a single entry.

    `key` extracts the value we compare on.
    For a bare string list use the default.
    For a list of dicts returned by safe_exec, pass:  key=lambda e: e['func']
    """
    return [next(g) for _, g in groupby(errs, key=key)]

def as_ratio(n: int, d: int) -> float:
    """Return n/d rounded to 4 dp; 0.0 if d == 0."""
    return 0.0 if d == 0 else round(n / d, 4)

# =========================== SCORING PART ===========================

def make_scores(
    tasks_path: str,
    prompts_path: str,
    code_logs_file: str | None,
    code_logs_dir: str,
    output_dir: str,
    skip_existing: bool,
    diff_start: int,
    diff_end: int,
    diff_step: int,
    diff_custom: list[int] | None,
    task_num: str,
    timeout: int,
    cutoff_actions: int,
) -> list[Path]:
    """
    Runs the scoring pass. Returns a list of produced *_scores.json files.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Load tasks & prompts once
    with open(tasks_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    with open(prompts_path, 'r', encoding='utf-8') as f:
        prompts = json.load(f)

    # Difficulties
    if diff_custom is not None:
        difficulties = diff_custom
    else:
        difficulties = list(range(diff_start, diff_end + 1, diff_step))
    print(f"[config] Difficulty list for this run: {difficulties}")

    # Build code_logs paths
    if code_logs_file is not None:
        code_logs_paths = [code_logs_file]
    else:
        pattern = os.path.join(code_logs_dir, "*code_logs*.json")
        code_logs_paths = glob.glob(pattern)

    if not code_logs_paths:
        print(f"[error] No code_logs files found in {code_logs_dir}!")
        return []

    produced = []

    for code_logs_path in code_logs_paths:
        fname   = os.path.basename(code_logs_path)
        prefix  = re.sub(r"_code_logs\.json$", "", fname)
        outpath = os.path.join(output_dir, f"{prefix}_scores.json")

        # per-model results for win/loss info
        results_path = os.path.join(os.path.dirname(code_logs_path), f"{prefix}.json")
        if not os.path.exists(results_path):
            raise FileNotFoundError(f"Couldn't find results file: {results_path}")
        with open(results_path, 'r', encoding='utf-8') as f:
            model_results = json.load(f)

        # Skip if exists and asked to
        if skip_existing and os.path.exists(outpath):
            print(f"[skip] Output already exists for `{fname}` ({os.path.basename(outpath)}), skipping.")
            produced.append(Path(outpath))  # still include it for downstream stats
            continue

        print(f"\n[run] Scoring `{fname}` → `{os.path.basename(outpath)}`")

        with open(code_logs_path, 'r', encoding='utf-8') as f:
            code_logs = json.load(f)

        scoring = {}

        for diff in difficulties:
            diff_key = str(diff)
            if diff_key not in code_logs:
                print(f"[warn] Difficulty {diff_key} not present in code_logs – skipping")
                continue

            scoring.setdefault(diff_key, {})
            task_list   = tasks.get(diff_key, [])
            prompt_list = prompts.get(diff_key, [])
            selected    = get_tasks_to_run(task_list, prompt_list, task_num)

            for idx, (task, prompt) in selected:
                task_type = get_task_type(prompt)
                if   task_type == 'kill':  tag = f"{idx}_{task['monster_name']}_kill"
                elif task_type == 'craft': tag = f"{idx}_{task['item']}_craft"
                else:
                    print(f"[warn] Unknown task type for index {idx}; skipping")
                    continue

                if tag not in code_logs[diff_key]:
                    print(f"[warn] No code for {diff_key}:{tag}; skipping")
                    continue

                codes = code_logs[diff_key][tag]["code"]
                # Get win/loss outcomes from the model_results file
                results_list = model_results.get(diff_key, {}).get(tag, {}).get("results", [])
                scoring[diff_key].setdefault(tag, [])
                print(f"[score] {diff_key}:{tag} – {len(codes)} sample(s)")

                for s, code in enumerate(codes):
                    try:
                        create_character('Hero', prompt)
                        sandbox = {"__name__": "__main__"}  
                        run_info = safe_exec(code, sandbox=sandbox, timeout=timeout)
                        logs = cut_events_before_creation(get_character_logs('Hero', cutoff_actions))
                        raw_errors  = run_info.get('func_errors', [])
                        func_errors = squash_consecutive_errors(
                            raw_errors,
                            key=(lambda e: e['func']) if raw_errors and isinstance(raw_errors[0], dict) else (lambda e: e)
                        )
                    except Exception as exc:
                        print(f"    [error] execution failed: {exc}")
                        logs = []
                        func_errors = []

                    logs_empty = (logs == [] or logs == [[]])
                    reward, actual_counts      = compute_episode_reward(task, logs)
                    ideal_reward, ideal_counts = compute_ideal_episode_reward(task)

                    # Determine win/lose from model_results, if available
                    outcome = None
                    if s < len(results_list):
                        outcome = results_list[s]    # "win" or "lose"
                    else:
                        outcome = "unknown"
                    is_win = (outcome == "win")

                    failed_keys = {}
                    if not is_win:
                        failed_keys = {
                            key: ideal_counts[key] - actual_counts.get(key, 0)
                            for key in ideal_counts
                            if actual_counts.get(key, 0) < ideal_counts[key]
                        }

                    result = {
                        "sample":      s,
                        "outcome":     outcome,       # "win" or "lose"
                        "win":         is_win,        # True/False
                        "reward":      reward,
                        "ideal_reward": ideal_reward,
                        "delta":       ideal_reward - reward,
                        "failed":      failed_keys,
                        "func_errors": func_errors,
                        "logs_empty":  logs_empty,
                    }
                    print(f"    sample {s}: {outcome.upper()} — reward {reward}/{ideal_reward}")
                    if not is_win and failed_keys:
                        print("        ↳ failed keys:", ", ".join(sorted(failed_keys)))

                    scoring[diff_key][tag].append(result)

        # Write results for this file
        with open(outpath, 'w', encoding='utf-8') as f:
            json.dump(scoring, f, indent=2)
        print(f"[done] Saved scores to {outpath}")
        produced.append(Path(outpath))

    return produced

# =========================== STATS PART ===========================

MISSING_RE = re.compile(r"(craft|obtain)_missing:(.+)")
CRAFT_INT_RE = re.compile(r"craft_intermediate:(.+)")
ARG_ITEM_RE = re.compile(r"\('.*?'\s*,\s*'(.*?)'\s*,")
WRONG_FORMAT_KEY = "tasks_with_wrong_code_format"
LOGS_EMPTY_KEY = "logs_empty"
OTHER_KEY = "tasks_other"

def scan_tasks(task_path: Path):
    """Pre-scan the task file once (unchanged)."""
    data = json.loads(task_path.read_text(encoding="utf-8"))
    base_missing = Counter()
    total_tasks = Counter()
    grand_missing = 0
    grand_tasks = 0
    for diff, tasks in data.items():
        for t in tasks:
            total_tasks[diff] += 1
            grand_tasks += 1
            if "monster_name" in t:
                n = len(t.get("missing_items", {}))
                base_missing[diff] += n
                grand_missing += n
    pure_item_tasks = Counter()
    for diff, tasks in data.items():
        for t in tasks:
            if "monster_name" not in t:
                pure_item_tasks[diff] += 1
    grand_pure_item_tasks = sum(pure_item_tasks.values())
    return (
        base_missing, grand_missing, total_tasks, grand_tasks,
        pure_item_tasks, grand_pure_item_tasks, data,
    )

def build_stats_for_one(
    in_file: Path,
    out_file: Path,
    task_data: dict,
    base_missing: Counter,
    grand_missing: int,
    total_tasks_cnt: Counter,
    grand_tasks: int,
    pure_item_tasks_cnt: Counter,
    grand_pure_item_tasks: int,
):
    """Produce *_stats.json with execution-error metrics and craft_missing_not_attempted."""
    scoring = json.loads(in_file.read_text(encoding="utf-8"))
    BASE_COUNTERS = {
        "execution_errors": {
            "total": 0,
            "by_func": Counter(),
            "craft_reasons": Counter(),
        },
        "craft_missing_not_attempted": 0,
        "tasks_with_only_failed_gear_calculation": 0,
        "tasks_failed_total": 0,
        "tasks_with_both_calc_craft": 0,
        "tasks_with_only_failed_craft": 0,
        "tasks_with_wrong_code_format": 0,
        "tasks_other": 0,
        "win_tasks": 0,
    }
    win_per_diff = Counter()
    win_total = 0
    raw_per_diff = {}
    raw_overall = copy.deepcopy(BASE_COUNTERS)

    for diff, tags in scoring.items():
        stats = copy.deepcopy(BASE_COUNTERS)
        for task_name, runs in tags.items():
            for run in runs:
                if run.get(LOGS_EMPTY_KEY, False):
                    stats[WRONG_FORMAT_KEY] += 1
                    raw_overall[WRONG_FORMAT_KEY] += 1
                    stats["tasks_failed_total"] += 1
                    raw_overall["tasks_failed_total"] += 1
                    continue
                if run.get("win", False) is True:
                    stats["win_tasks"] += 1
                    raw_overall["win_tasks"] += 1
                    win_per_diff[diff] += 1
                    win_total += 1
                    continue

                failed = run.get("failed") or run.get("missing") or {}
                func_errors = run.get("func_errors", [])
                failure_keys = failed.keys()
                has_craft_missing = any(k.startswith("craft_missing:") for k in failure_keys)
                has_obtain_missing = any(k.startswith("obtain_missing:") for k in failure_keys)
                has_missing = has_craft_missing or has_obtain_missing
                has_func_errors = bool(func_errors)
                is_craft_task = task_name.endswith("_craft")
                is_kill_task = task_name.endswith("_kill")
                has_failed = bool(failed)

                attempted_codes = set()
                for err in func_errors:
                    if err.get("func") == "craft":
                        m = ARG_ITEM_RE.search(err.get("args", ""))
                        if m:
                            attempted_codes.add(m.group(1))

                # legacy metric: craft_missing_not_attempted
                if has_craft_missing:
                    craft_missing_items = {
                        k.split(":", 1)[1]
                        for k in failure_keys
                        if k.startswith("craft_missing:")
                    }
                    not_attempted = craft_missing_items - attempted_codes
                    cmna = len(not_attempted)
                    if cmna:
                        stats["craft_missing_not_attempted"] += cmna
                        raw_overall["craft_missing_not_attempted"] += cmna

                # bucket logic
                if has_missing and not has_func_errors:
                    stats["tasks_with_only_failed_gear_calculation"] += 1
                    raw_overall["tasks_with_only_failed_gear_calculation"] += 1
                elif (not has_missing) and has_failed and is_kill_task:
                    stats[OTHER_KEY] += 1
                    raw_overall[OTHER_KEY] += 1
                elif (
                    (has_craft_missing and attempted_codes >= {k.split(":", 1)[1] for k in failure_keys if k.startswith("craft_missing:")})
                    or is_craft_task
                ) and has_failed:
                    stats["tasks_with_only_failed_craft"] += 1
                    raw_overall["tasks_with_only_failed_craft"] += 1
                elif has_failed:
                    stats["tasks_with_both_calc_craft"] += 1
                    raw_overall["tasks_with_both_calc_craft"] += 1

                stats["tasks_failed_total"] += 1
                raw_overall["tasks_failed_total"] += 1

                # execution error counters
                for err in func_errors:
                    func = err.get("func", "<unknown>")
                    # Only count equip errors with "Slot is not empty."
                    if func == "equip":
                        if err.get("message") != "Slot is not empty.":
                            continue
                    stats["execution_errors"]["total"] += 1
                    raw_overall["execution_errors"]["total"] += 1
                    stats["execution_errors"]["by_func"][func] += 1
                    raw_overall["execution_errors"]["by_func"][func] += 1
                    if func == "craft":
                        msg = err.get("message")
                        if isinstance(msg, dict):
                            errors_dict = msg.get("errors", {})
                            for reason, flag in errors_dict.items():
                                if flag is False:
                                    stats["execution_errors"]["craft_reasons"][reason] += 1
                                    raw_overall["execution_errors"]["craft_reasons"][reason] += 1

        raw_per_diff[diff] = stats

    # Build relative view (counts only for execution_errors stay raw counts)
    out_per_diff = {}
    for diff, stats in raw_per_diff.items():
        dt = total_tasks_cnt[diff]
        out_per_diff[diff] = {
            "execution_errors": {
                "total": stats["execution_errors"]["total"],
                "by_func": dict(stats["execution_errors"]["by_func"]),
                "craft_reasons": dict(stats["execution_errors"]["craft_reasons"]),
            },
            "craft_missing_not_attempted": stats["craft_missing_not_attempted"],
            "tasks_with_only_failed_gear_calculation": as_ratio(stats["tasks_with_only_failed_gear_calculation"], dt),
            "tasks_failed_total": as_ratio(stats["tasks_failed_total"], dt),
            "tasks_with_both_calc_craft": as_ratio(stats["tasks_with_both_calc_craft"], dt),
            "tasks_with_only_failed_craft": as_ratio(stats["tasks_with_only_failed_craft"], dt),
            "tasks_with_wrong_code_format": as_ratio(stats["tasks_with_wrong_code_format"], dt),
            "tasks_other": as_ratio(stats["tasks_other"], dt),
            "win_tasks": stats["win_tasks"],
        }

    # Grand total (relative to total tasks)
    dt_total = grand_tasks
    out_per_diff["total"] = {
        "execution_errors": {
            "total": raw_overall["execution_errors"]["total"],
            "by_func": dict(raw_overall["execution_errors"]["by_func"]),
            "craft_reasons": dict(raw_overall["execution_errors"]["craft_reasons"]),
        },
        "craft_missing_not_attempted": raw_overall["craft_missing_not_attempted"],
        "tasks_with_only_failed_gear_calculation": as_ratio(raw_overall["tasks_with_only_failed_gear_calculation"], dt_total),
        "tasks_failed_total": as_ratio(raw_overall["tasks_failed_total"], dt_total),
        "tasks_with_both_calc_craft": as_ratio(raw_overall["tasks_with_both_calc_craft"], dt_total),
        "tasks_with_only_failed_craft": as_ratio(raw_overall["tasks_with_only_failed_craft"], dt_total),
        "tasks_with_wrong_code_format": as_ratio(raw_overall["tasks_with_wrong_code_format"], dt_total),
        "tasks_other": as_ratio(raw_overall["tasks_other"], dt_total),
        "win_tasks": raw_overall["win_tasks"],
    }

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(out_per_diff, indent=2), encoding="utf-8")
    print(
        f"[done] {out_file.name:40}  "
        f"exec_errors={raw_overall['execution_errors']['total']:>5}  "
        f"cm_not_attempted={raw_overall['craft_missing_not_attempted']:>4}  "
        f"tasks={dt_total}  "
        f"win_tasks={raw_overall['win_tasks']}"
    )

def make_stats(stats_input: Path, tasks_path: Path):
    """
    Build *_stats.json for either a single *_scores.json file or all of them in a directory.
    """
    (
        base_missing,
        grand_missing,
        total_tasks_cnt,
        grand_tasks,
        pure_item_tasks_cnt,
        grand_pure_item_tasks,
        task_data,
    ) = scan_tasks(tasks_path)

    if stats_input.is_file():
        inputs = [stats_input]
    elif stats_input.is_dir():
        inputs = sorted(stats_input.glob("*_scores.json"))
    else:
        raise RuntimeError(f"{stats_input} is neither file nor directory")

    if not inputs:
        print("No *_scores.json files found.")
        return

    for in_file in inputs:
        stem = in_file.stem
        base = stem[:-7] if stem.endswith("_scores") else stem
        out_file = in_file.parent / f"{base}_stats.json"
        build_stats_for_one(
            in_file,
            out_file,
            task_data,
            base_missing,
            grand_missing,
            total_tasks_cnt,
            grand_tasks,
            pure_item_tasks_cnt,
            grand_pure_item_tasks,
        )

# =============================== CLI ===============================

def parse_args():
    p = argparse.ArgumentParser(description="Run scoring and/or stats.")
    p.add_argument("--mode", choices=["both", "scoring", "stats"], default="both")

    # scoring args
    p.add_argument("--tasks_path", default="datasets/dataset_tasks.json")
    p.add_argument("--prompts_path", default="datasets/dataset_prompts.json")
    p.add_argument("--code_logs_file", default=None)
    p.add_argument("--code_logs_dir", default="results/results_base")
    p.add_argument("--output_dir", default="results/results_base_scoring")
    p.add_argument("--skip_existing", action="store_true")
    p.add_argument("--diff_start", type=int, default=1)
    p.add_argument("--diff_end", type=int, default=9)
    p.add_argument("--diff_step", type=int, default=1)
    p.add_argument("--diff_custom", default=None, help='Comma-separated list, e.g. "1,3,5"')
    p.add_argument("--task_num", default="all")
    p.add_argument("--timeout", type=int, default=100)
    p.add_argument("--cutoff_actions", type=int, default=4000)

    # stats args
    p.add_argument("--stats_input", default=None, help="Path to *_scores.json or a directory; defaults to --output_dir")

    return p.parse_args()

def main():
    args = parse_args()

    # Parse diff_custom if provided
    diff_custom = None
    if args.diff_custom:
        diff_custom = [int(x.strip()) for x in args.diff_custom.split(",") if x.strip()]

    produced_scores = []
    if args.mode in ("both", "scoring"):
        produced_scores = make_scores(
            tasks_path=args.tasks_path,
            prompts_path=args.prompts_path,
            code_logs_file=args.code_logs_file,
            code_logs_dir=args.code_logs_dir,
            output_dir=args.output_dir,
            skip_existing=args.skip_existing,
            diff_start=args.diff_start,
            diff_end=args.diff_end,
            diff_step=args.diff_step,
            diff_custom=diff_custom,
            task_num=args.task_num,
            timeout=args.timeout,
            cutoff_actions=args.cutoff_actions,
        )

    if args.mode in ("both", "stats"):
        stats_input = Path(args.stats_input) if args.stats_input else Path(args.output_dir)
        make_stats(stats_input=stats_input, tasks_path=Path(args.tasks_path))

if __name__ == "__main__":
    mp.freeze_support()
    main()
