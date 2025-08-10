import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from Virtual_Environment.api_calls import *
from utils import *



# ===============================================================
#                USER CONFIGURATION SECTION
# 
# Adjust the following parameters to control how the script runs.
# Most users only need to modify these variables:
#
# - TASKS_PATH, PROMPTS_PATH: Input data files (JSON)
# - RESULTS_DIR: Directory to save results
# - DIFF_START, DIFF_END, DIFF_STEP: Difficulty sweep (or DIFF_CUSTOM for explicit list)
# - TASK_NUM: Which tasks to run ('all', a single number, or a range '12-18')
# - SAVE_NAME: Prefix for output files
# - SAMPLES: Number of model samples per task
# - TIMEOUT: Max seconds per model-generated code execution
# - CUTOFF_ACTIONS: Truncate logs for long episodes
# - RESUME: Continue from previous results if results file exists
# - OVERWRITE_MODE: Overwrite behavior for existing results ('all', 'lose', '0', 'none')

# LLMService unifies access to multiple LLM providers with optional controls.
#
# --- Main Initialization Arguments ---
# - service:        "openai", "ollama", "hf", "openrouter", or "openrouter_openai" for using openai models through openrouter
# - model_name:     Name/ID of the model for the selected provider
# - openai_key:     Required for OpenAI and OpenRouter APIs
# - max_tokens:     Limits reasoning generation length (see provider/model-specific notes below)
# - reasoning_effort: Controls step-by-step reasoning level (see provider/model notes)
# - streaming:      If True, enables streaming (HF only)
# - thinking:       (HF Qwen only) Enables Qwen "thinking mode" (internal self-reflection)
#
# --- Provider/Model-Specific Options ---
# 1. OpenAI, OpenaAI with openrouter
#    - Use `reasoning_effort` to control reasoning steps/detail (if supported by the model). Accepts "low", "medium" or " high".
#
# 2. OpenRouter
#    - Use `max_tokens` for **Google** and **Anthropic** models 
#         (sets reasoning/max_tokens in the payload).
#
# 3. HuggingFace ("hf")
#    - Set `thinking=True` for Qwen3 models to enable their "thinking" mode.
#    - `max_tokens` and `reasoning_effort` do not affect HuggingFace models.
#
# ===============================================================


# ======================== CONFIGURATION ========================
TASKS_PATH        = "datasets/dataset_tasks_noise_leveling.json"
PROMPTS_PATH      = "datasets/dataset_prompts_noise_leveling.json"
RESULTS_DIR       = "results/results_hard"

DIFF_START        = 9
DIFF_END          = 9
DIFF_STEP         = 1
DIFF_CUSTOM       = None      # List[int] or None
TASK_NUM          = 'all'     # 'all', '12', or '12-18'
SAVE_NAME         = 'gpt-5-noise_level'
SAMPLES           = 1
TIMEOUT           = 100
CUTOFF_ACTIONS    = 4000
RESUME            = True
OVERWRITE_MODE    = 'none'     # 'all', 'lose', '0', 'none'

# LLM service configuration
LLM_SERVICE_CFG = dict(
    service="openai",
    model_name="gpt-5",
    max_tokens=40000,
    reasoning_effort="high",
    api_key="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",
    streaming=False,
    thinking=False
)
# ===============================================================

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def load_json_file(path: str) -> Any:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load {path}: {e}")
        return {}

def save_json_file(data: Any, path: str):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save {path}: {e}")

def main():
    setup_logging()

    results_dir = RESULTS_DIR
    os.makedirs(results_dir, exist_ok=True)

    combined_path    = os.path.join(results_dir, f"{SAVE_NAME}.json")
    code_logs_path   = os.path.join(results_dir, f"{SAVE_NAME}_code_logs.json")
    full_logs_path   = os.path.join(results_dir, f"{SAVE_NAME}_full_log.json")

    # Resume or initialize logs
    if RESUME and os.path.exists(combined_path):
        combined   = load_json_file(combined_path)
        code_logs  = load_json_file(code_logs_path)
        full_logs  = load_json_file(full_logs_path)
        logging.info(f"Loaded existing results for difficulties: {sorted(combined.keys())}")
    else:
        combined, code_logs, full_logs = {}, {}, {}
        logging.info("Starting fresh run")

    # Difficulty setup
    if DIFF_CUSTOM is not None:
        difficulties = DIFF_CUSTOM
    else:
        difficulties = list(range(DIFF_START, DIFF_END + 1, DIFF_STEP))
    logging.info(f"Difficulty list for this run: {difficulties}")

    # Load data
    tasks   = load_json_file(TASKS_PATH)
    prompts = load_json_file(PROMPTS_PATH)

    client = LLMService(**LLM_SERVICE_CFG)

    # Main loop
    for difficulty in difficulties:
        diff_key = str(difficulty)
        if diff_key not in tasks or diff_key not in prompts:
            logging.warning(f"Difficulty {difficulty} not present in data files – skipped")
            continue

        combined.setdefault(diff_key, {})
        code_logs.setdefault(diff_key, {})
        full_logs.setdefault(diff_key, {})

        task_list   = tasks[diff_key]
        prompt_list = prompts[diff_key]
        to_run      = get_tasks_to_run(task_list, prompt_list, TASK_NUM)

        if not to_run:
            logging.info(f"No tasks selected at difficulty {difficulty}")
            continue

        for idx, (task, prompt_str) in to_run:
            task_type = get_task_type(prompt_str)
            if task_type == 'kill':
                tag = f"{idx}_{task['monster_name']}_kill"
            elif task_type == 'craft':
                tag = f"{idx}_{task['item']}_craft"
            else:
                logging.warning(f"Unknown task type for index {idx}; skipping")
                continue

            # Overwrite/skip logic
            should_run = True
            prev = combined[diff_key].get(tag)
            if prev is not None:
                if OVERWRITE_MODE == 'all':
                    should_run = True
                elif OVERWRITE_MODE == 'lose':
                    if not any(r == 'lose' for r in prev['results']):
                        logging.info(f"Skip {diff_key}:{tag} (no failures); mode=lose")
                        should_run = False
                elif OVERWRITE_MODE == '0':
                    if not any(reward == 0 for reward in prev['rewards']):
                        logging.info(f"Skip {diff_key}:{tag} (no zero-reward runs); mode=0")
                        should_run = False
                elif OVERWRITE_MODE == 'none':
                    logging.info(f"Skip {diff_key}:{tag} (already exists); mode=none")
                    should_run = False
                else:
                    raise ValueError(f"Invalid OVERWRITE_MODE: {OVERWRITE_MODE}")

            if not should_run:
                continue

            logging.info(f"Running Difficulty {diff_key} task {tag} – {SAMPLES} sample(s)")

            # Run model
            run_task(
                client, task, prompt_str, diff_key, tag, SAMPLES, TIMEOUT, CUTOFF_ACTIONS,
                combined, code_logs, full_logs
            )

            # Persist results after each task
            save_json_file(combined, combined_path)
            save_json_file(code_logs, code_logs_path)
            save_json_file(full_logs, full_logs_path)

def run_task(
    client, task, prompt_str, diff_key, tag, samples, timeout, cutoff_actions,
    combined, code_logs, full_logs
):
    results, tokens, codes, logs_list = [], [], [], []
    rewards, ideal_rewards, scores = [], [], []
    full_responses = []
    difficulty_val = task.get("total_difficulty")

    for _ in range(samples):
        answer, full_response, out_tok, cost = client.generate(prompt_str)
        logging.info(f"[LLM] cost: {cost}")

        code = extract_final_code(answer)
        create_character('Hero', prompt_str)

        try:
            safe_exec(code, globals(), locals(), timeout=timeout)
            logs   = cut_events_before_creation(get_character_logs('Hero', cutoff_actions))
            result = extract_result(logs, prompt_str, task)
        except Exception as e:
            logging.error(f"Execution failed: {e}")
            logs, result = [], 'lose'

        reward, _       = compute_episode_reward(task, logs)
        ideal_reward, _ = compute_ideal_episode_reward(task)
        score           = reward * 100.0 / ideal_reward if ideal_reward else 0.0

        results.append(result)
        tokens.append(out_tok)
        codes.append(code)
        logs_list.append(logs)
        rewards.append(reward)
        ideal_rewards.append(ideal_reward)
        scores.append(score)
        full_responses.append(full_response)

    combined[diff_key][tag] = {
        "difficulty": difficulty_val,
        "results": results,
        "tokens": tokens,
        "rewards": rewards,
        "ideal_rewards": ideal_rewards,
        "scores": scores,
    }
    code_logs[diff_key][tag] = {
        "code": codes,
        "logs": logs_list,
    }
    full_logs[diff_key][tag] = full_responses

if __name__ == "__main__":
    main()
