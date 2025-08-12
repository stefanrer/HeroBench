import json
import os
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D

PLOTS_DIR = "results/plots_tables"
os.makedirs(PLOTS_DIR, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.linestyle": "--",
    "grid.alpha": 0.25,
    "font.size": 13,
    "axes.titleweight": "bold",
})

MODEL_SPECS = {
    "Qwen3-8b":                     {"path": "results/results_base/qwen3_8b.json",                    "think": False},
    "Qwen3-8b think":               {"path": "results/results_base/qwen3_8b_think.json",              "think": True},
    "Qwen3-32b":                    {"path": "results/results_base/qwen3_32b.json",                   "think": False},
    "Qwen3-32b think":              {"path": "results/results_base/qwen3_32b_think.json",             "think": True},
    "Qwen3-235b-a22b":              {"path": "results/results_base/qwen3-235b-a22.json",              "think": True},
    "Qwen3-235b-a22b-2507":         {"path": "results/results_base/qwen3-235b-a22b-thinking-2507.json","think": True},
    "GigaChat-2-Max":               {"path": "results/results_base/gigachat-2-max.json",                 "think": False},
    "Deepseek-V3":                  {"path": "results/results_base/deepseek-v3.json",                 "think": False},
    "Deepseek-R1-0528":             {"path": "results/results_base/deepseek-r1-0528.json",            "think": True},
    "DeepSeek-R1-70B":              {"path": "results/results_base/DeepSeek-R1-Distill-Llama-70B.json","think": True},
    "Gemini-2.5-pro":               {"path": "results/results_base/gemini-2.5-pro.json",              "think": True},
    "Gemini-2.5-flash":             {"path": "results/results_base/gemini-2.5-flash.json",            "think": True},
    "Claude-Sonnet-4":              {"path": "results/results_base/claude-sonnet-4.json",             "think": False},
    "Claude-Sonnet-4 think":        {"path": "results/results_base/claude-sonnet-4_think.json",       "think": True},
    "GPT-4.1-mini":                 {"path": "results/results_base/gpt4.1_mini.json",                 "think": False},
    "GPT-4.1":                      {"path": "results/results_base/gpt-4.1.json",                     "think": False},
    "o4-mini":                      {"path": "results/results_base/o4-mini_high.json",                "think": True},
    "o3":                           {"path": "results/results_base/o3_high.json",                     "think": True},
    "GPT-oss-120b":                 {"path": "results/results_base/gpt-oss-120b.json",                     "think": True},
    "GPT-5-mini":                   {"path": "results/results_base/gpt-5-mini.json",                     "think": True},
    "GPT-5":                        {"path": "results/results_base/gpt-5.json",                     "think": True},
    "Magistral-medium-2506":        {"path": "results/results_base/magistral-medium-2506-thinking.json","think": True},
    "Grok-4":                       {"path": "results/results_base/grok-4.json",                      "think": True},
    "Kimi-K2":                      {"path": "results/results_base/kimi-k2.json",                     "think": False},
}

def analyze_results(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    difficulties, success_rates, avg_scores, avg_tokens = [], [], [], []
    for diff_str, tasks in sorted(data.items(), key=lambda x: float(x[0])):
        all_results, all_scores, all_tokens = [], [], []
        for task_data in tasks.values():
            all_results.extend(task_data.get("results", []))
            all_scores.extend(task_data.get("scores", []))
            all_tokens.extend(task_data.get("tokens", []))
        num = len(all_results)
        wins = sum(1 for r in all_results if r == "win")
        success = wins / num if num else 0
        score = (sum(all_scores) / len(all_scores)) if all_scores else 0
        valid_tokens = [t for t in all_tokens if t is not None]
        tokens = (sum(valid_tokens) / len(valid_tokens)) if valid_tokens else 0

        difficulties.append(float(diff_str))
        success_rates.append(success)
        avg_scores.append(score)
        avg_tokens.append(tokens)
    return difficulties, success_rates, avg_scores, avg_tokens

def family_of(display_name: str):
    lower = display_name.lower()
    if lower.startswith("qwen3"): return "qwen"
    if lower.startswith("deepseek"): return "deepseek"
    if lower.startswith("gemini"): return "gemini"
    if "claude" in lower: return "claude"
    if lower.startswith("gpt") or lower.startswith("o"): return "gpt"
#    if lower.startswith("o4") or lower.startswith("o3"): return "openai-o"
    if lower.startswith("magistral"): return "magistral"
    if lower.startswith("grok-4"): return "grok"
    if lower.startswith("kimi"): return "kimi"
    return "other"

FAMILY_COLORS = {
    "qwen": "#1f77b4",       
    "deepseek": "#d62728",
    "gemini": "#2ca02c",
    "claude": "#9467bd",
    "gpt": "#ff9800",    
    "openai-o": "#ffa733",   
    "magistral": "#8c564b",
    "grok": "#e377c2",
    "kimi": "#7f7f7f",
    "other": "#00a17e",
}

def color_for(display_name: str):
    return FAMILY_COLORS.get(family_of(display_name), FAMILY_COLORS["other"])

def style_for(think: bool):
    return "-" if think else "--"

def legend_order_key(name: str):
    return (family_of(name), name)


def add_style_legend(ax, loc="upper right", anchor=(0.98, 0.98)):
    think_line = Line2D([], [], linestyle='-',  color='black', label='Thinking')
    non_line   = Line2D([], [], linestyle='--', color='black', label='Non-thinking')
    style_leg = ax.legend(
        handles=[think_line, non_line],
        loc=loc,
        bbox_to_anchor=anchor,
        frameon=False,
        fontsize=12,
        handlelength=2.8,
    )
    return style_leg

# ─────────────────────────────────────────────────────────
# Load metrics
# ─────────────────────────────────────────────────────────
all_metrics = {}
for display_name, spec in MODEL_SPECS.items():
    diffs, succ, scores, toks = analyze_results(spec["path"])
    all_metrics[display_name] = {
        'difficulty': diffs,
        'success_rate': succ,
        'avg_score': scores,
        'avg_tokens': toks,
        'think': spec["think"]
    }

model_names = sorted(all_metrics.keys(), key=legend_order_key)

# ─────────────────────────────────────────────────────────
# Generate per‐model shades within each family
# ─────────────────────────────────────────────────────────
family_groups = defaultdict(list)
for name in model_names:
    family_groups[family_of(name)].append(name)

family_shades = {}
for family, names in family_groups.items():
    base_rgb = np.array(mcolors.to_rgb(FAMILY_COLORS[family]))
    n = len(names)
    for i, name in enumerate(names):
        if n > 1:
            factor = 0.5 + (i / (n - 1)) * 0.5
        else:
            factor = 1.0
        shade_rgb = base_rgb * factor + (1 - factor) * np.ones(3)
        family_shades[name] = mcolors.to_hex(shade_rgb)

# Override color_for to use these shades
def color_for(display_name: str):
    return family_shades.get(
        display_name,
        FAMILY_COLORS.get(family_of(display_name), FAMILY_COLORS["other"])
    )

# ─────────────────────────────────────────────────────────
# Assign marker per model within each family  
# ─────────────────────────────────────────────────────────

FAMILY_MARKERS = [
    "o", "s", "^", "v", "D", "P", "X", "*", "p", "h", "<", ">", "8", "|", "_"
]
model_marker = {}

for family, names in family_groups.items():
    markers = FAMILY_MARKERS.copy()
    if len(names) > len(markers):
        # If too many, repeat or extend
        markers = (FAMILY_MARKERS * ((len(names) // len(FAMILY_MARKERS)) + 1))
    for name, marker in zip(names, markers):
        model_marker[name] = marker

def marker_for(name: str):
    return model_marker.get(name, "o")
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

# ─────────────────────────────────────────────────────────
# Shared plotting helpers
# ─────────────────────────────────────────────────────────
def add_multi_column_legend(ax, ncol=4, ypad=-0.18):
    handles, labels = ax.get_legend_handles_labels()
    label_to_handle = {lab: h for h, lab in zip(handles, labels)}

    ordered_handles = [label_to_handle[m] for m in model_names if m in label_to_handle]

    # Add style explanation entries (dummy lines)
    think_line, = ax.plot([], [], linestyle='-', color='black', label='Thinking')
    non_line,   = ax.plot([], [], linestyle='--', color='black', label='"Non-thinking')

    ordered_handles.extend([think_line, non_line])
    ordered_labels = model_names + ["Thinking", "Non-thinking"]

    ax.legend(
        ordered_handles,
        ordered_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, ypad),
        ncol=ncol,
        fontsize=15,
        frameon=False,
        columnspacing=1.2,
        handlelength=2.8,
        borderaxespad=0.0
    )

def finalize_axes(ax, xlabel, ylabel, title, ypad=0.02):
    ax.set_xlabel(xlabel, labelpad=6)
    ax.set_ylabel(ylabel, labelpad=6)
    ax.set_title(title, pad=14)
    if all(d == int(d) for d in ax.get_xticks()):
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    if ylabel.lower().startswith("success"):
        ax.set_ylim(-ypad, 1+ypad)
    ax.grid(True)

# ─────────────────────────────────────────────────────────
# Line plots
# ─────────────────────────────────────────────────────────
def plot_metric(metric_key, ylabel, title, out_path, ylim=None):
    fig, ax = plt.subplots(figsize=(14, 7))
    for name in model_names:
        mm = all_metrics[name]
        ax.plot(
            mm['difficulty'],
            mm[metric_key],
            label=name,
            color=color_for(name),
            linestyle=style_for(mm['think']),
            linewidth=2.2,
            marker=marker_for(name),      # <<<<<<<<<<<<<<<<<<<
            markersize=7
        )
    finalize_axes(ax, "Difficulty", ylabel, title)
    if ylim:
        ax.set_ylim(*ylim)
    add_multi_column_legend(ax, ncol=4)
    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


plot_metric('success_rate', 'Success Rate', 'Success rate on base tasks',
            f'{PLOTS_DIR}/success_rate_improved.png', ylim=(0,1.02))
plot_metric('avg_score', 'Average Score', 'Average Score vs Difficulty',
            f'{PLOTS_DIR}/average_score_improved.png')
plot_metric('avg_tokens', 'Average Tokens', 'Average Tokens vs Difficulty',
            f'{PLOTS_DIR}/average_tokens_improved.png')

# ─────────────────────────────────────────────────────────
# Summary stats & bar charts
# ─────────────────────────────────────────────────────────
mean_success = [np.mean(all_metrics[m]['success_rate']) for m in model_names]
mean_score   = [np.mean(all_metrics[m]['avg_score'])     for m in model_names]
mean_tokens  = [np.mean(all_metrics[m]['avg_tokens'])    for m in model_names]

norm_success = [s/t if t else 0 for s, t in zip(mean_success, mean_tokens)]
norm_score   = [sc/t if t else 0 for sc, t in zip(mean_score, mean_tokens)]

def save_bar_chart(xlabels, values, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(14, 7))
    indices = np.arange(len(xlabels))
    max_val = max(values) if values else 1
    for i, name in enumerate(xlabels):
        col = color_for(name)
        hatch = None if all_metrics[name]['think'] else "//"
        ax.bar(i, values[i], color=col, edgecolor='black',
               linewidth=0.7, hatch=hatch, alpha=0.85)

    ax.set_ylabel(ylabel)
    ax.set_title(title, pad=14)
    ax.set_xticks(indices)
    ax.set_xticklabels(xlabels, rotation=40, ha='right')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    for i, v in enumerate(values):
        ax.text(i, v + (0.01 * max_val),
                f"{v:.2f}", ha='center', va='bottom', fontsize=9, rotation=90)
    plt.tight_layout()
    plt.savefig(filename, bbox_inches="tight")
    plt.close(fig)

save_bar_chart(model_names, mean_success, 'Mean Success Rate',
               'Mean Success Rate Across Difficulties',
               f'{PLOTS_DIR}/bar_mean_success_improved.png')

save_bar_chart(model_names, mean_score, 'Mean Score',
               'Mean Score Across Difficulties',
               f'{PLOTS_DIR}/bar_mean_score_improved.png')

save_bar_chart(model_names, norm_success, 'Success / Token',
               'Mean Success Rate per Token',
               f'{PLOTS_DIR}/bar_norm_success_improved.png')

save_bar_chart(model_names, norm_score, 'Score / Token',
               'Mean Score per Token',
               f'{PLOTS_DIR}/bar_norm_score_improved.png')
