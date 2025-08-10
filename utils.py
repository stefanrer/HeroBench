import os
import re
import json
import importlib
from Virtual_Environment.api_calls import*
import threading
from typing import Tuple, Optional

import multiprocessing
import traceback
from typing import Dict, List, Any
from collections import defaultdict
from pathlib import Path

import crafting_tree as ct       
import io, contextlib, traceback

import multiprocessing as mp
import traceback, contextlib, io



_API_TO_WRAP = ["move", "fight", "equip", "unequip", "gather", "craft"]

# ---------------------------------------------------------------------------
#  Helper: consistent monster key normalization
# ---------------------------------------------------------------------------
def norm_monster(name: str) -> str:
    """Normalize monster names for consistent keys."""
    return re.sub(r'\s+', ' ', name.strip().lower())

def _add(breakdown: dict, key: str) -> int:
    """Increment a breakdown entry and return +1 for total."""
    breakdown[key] = breakdown.get(key, 0) + 1
    return 1

_ANGLE_WRAP = re.compile(r'^\s*<\s*(.*?)\s*>\s*$', re.DOTALL)

def _strip_angle_wrapping(s: str) -> str:
    s = s.strip()
    m = _ANGLE_WRAP.match(s)
    return m.group(1).strip() if m else s

# ---------------------------------------------------------------------------
#  Scoring weights
# ---------------------------------------------------------------------------
WEIGHTS = {
    'target_win':          1,
    'craft_missing':       1,
    'equip_missing':       1,
    'obtain_missing':      1,
    'other_monster':       1,
    'gather_resource':     1,
    'craft_intermediate':  1,
    'buy_resource':        1,
}

# ---------------------------------------------------------------------------
#  Regex patterns
# ---------------------------------------------------------------------------
R_FIGHT = re.compile(
    r"\b(?P<result>win|lost) (?:his|their|your)? fight against (?P<monster>[\w\s&']+)",
    re.I
)
R_CRAFT  = re.compile(r"crafts (\w+) x", re.I)
R_EQUIP  = re.compile(r"equipped item (\w+)", re.I)
R_GATHER = re.compile(
    r"gathered resources\s+([\w_]+(?:\s*,\s*[\w_]+)*)(?=\s+with|$)",
    re.I
)
R_BUY    = re.compile(r"(?:bought|purchased)\s+(\w+)", re.I)

# ---------------------------------------------------------------------------
#  Helper: gatherable leaf resources in a crafting tree
# ---------------------------------------------------------------------------
def gatherable_resources(tree: dict) -> set[str]:
    if tree.get('basic'):
        return {tree['code']}
    need = set()
    for sub in tree['craft']['ingredients']:
        need |= gatherable_resources(sub)
    return need

# ---------------------------------------------------------------------------
#  Public API: route tasks to correct scorer
# ---------------------------------------------------------------------------
def compute_episode_reward(task: dict, logs: list[dict]) -> tuple[int, dict[str,int]]:
    is_kill = bool(task.get('monster_name'))
    return _reward_kill(task, logs) if is_kill else _reward_craft(task, logs)

# ---------------------------------------------------------------------------
#  Kill-and-Craft tasks
# ---------------------------------------------------------------------------
def _reward_kill(task: dict, logs: list[dict]) -> tuple[int, dict[str,int]]:
    target   = task.get('monster_name','').lower()
    missing  = set(task['missing_items'].values())

    # Required basic resources
    required_resources = set()
    for code in missing:
        tree = ct.build_crafting_tree(ct.items_by_code[code])
        required_resources |= gatherable_resources(tree)

    # Intermediate codes
    intermediate = set()
    def _collect(tree: dict):
        if 'craft' in tree:
            code = tree['code']
            if code not in missing:
                intermediate.add(code)
            for ing in tree['craft']['ingredients']:
                _collect(ing)
    for code in missing:
        _collect(ct.build_crafting_tree(ct.items_by_code[code]))

    # Drop sources: code -> monsters
    drop_sources = defaultdict(set)
    for code in missing:
        for d in ct.drops_by_item.get(code, []):
            drop_sources[code].add(d['name'])

    got_target = False
    beaten     = set()
    crafted_m  = set()
    crafted_i  = set()
    equipped   = set()
    obtained   = set()
    gathered   = set()
    total      = 0
    breakdown  = defaultdict(int)

    for entry in logs:
        line = entry['log']

        # – Fight –
        if m := R_FIGHT.search(line):
            res = m.group('result').lower()
            mon_raw = m.group('monster')
            mon = norm_monster(mon_raw)

            if res in ('win','wins','won'):
                if mon == target:
                    if not got_target:
                        total += WEIGHTS['target_win']
                        breakdown['target_win'] += WEIGHTS['target_win']
                        got_target = True
                else:
                    if mon not in beaten:
                        total += WEIGHTS['other_monster']
                        breakdown[f'other_monster:{mon}'] += WEIGHTS['other_monster']
                        beaten.add(mon)

                # Drops
                for code, mons in drop_sources.items():
                    normalized = {norm_monster(x) for x in mons}
                    if code not in obtained and mon in normalized:
                        total += WEIGHTS['obtain_missing']
                        breakdown[f'obtain_missing:{code}'] += WEIGHTS['obtain_missing']
                        obtained.add(code)

        # – Craft –
        if c := R_CRAFT.search(line):
            code = c.group(1).lower()
            if code in missing and code not in crafted_m:
                total += WEIGHTS['craft_missing']
                breakdown[f'craft_missing:{code}'] += WEIGHTS['craft_missing']
                crafted_m.add(code)
            elif code in intermediate and code not in crafted_i:
                total += WEIGHTS['craft_intermediate']
                breakdown[f'craft_intermediate:{code}'] += WEIGHTS['craft_intermediate']
                crafted_i.add(code)

        # – Equip –
        if e := R_EQUIP.search(line):
            code = e.group(1).lower()
            if code in missing and code not in equipped:
                total += WEIGHTS['equip_missing']
                breakdown[f'equip_missing:{code}'] += WEIGHTS['equip_missing']
                equipped.add(code)

        # – Gather –
        if g := R_GATHER.search(line):
            for r in [r.strip().lower() for r in g.group(1).split(',')]:
                if r in required_resources and r not in gathered:
                    total += WEIGHTS['gather_resource']
                    breakdown[f'gather_resource:{r}'] += WEIGHTS['gather_resource']
                    gathered.add(r)

    return total, dict(breakdown)

# ---------------------------------------------------------------------------
#  Pure-Craft tasks
# ---------------------------------------------------------------------------
def _reward_craft(task: dict, logs: list[dict]) -> tuple[int, dict[str,int]]:
    tree   = task['crafting_tree']
    target = tree['code'].lower()

    intermediate = set()
    basic        = set()
    def _walk(t: dict):
        c = t['code'].lower()
        if 'craft' in t:
            if c != target:
                intermediate.add(c)
            for ing in t['craft']['ingredients']:
                _walk(ing)
        else:
            basic.add(c)
    _walk(tree)

    crafted_t = False
    crafted_i = set()
    gathered  = set()
    bought    = set()
    total     = 0
    breakdown = defaultdict(int)

    for entry in logs:
        line = entry['log']

        if c := R_CRAFT.search(line):
            code = c.group(1).lower()
            if code == target and not crafted_t:
                total += WEIGHTS['target_win']
                breakdown['target_win'] += WEIGHTS['target_win']
                crafted_t = True
            elif code in intermediate and code not in crafted_i:
                total += WEIGHTS['craft_intermediate']
                breakdown[f'craft_intermediate:{code}'] += WEIGHTS['craft_intermediate']
                crafted_i.add(code)

        if g := R_GATHER.search(line):
            for r in [r.strip().lower() for r in g.group(1).split(',')]:
                if r in basic and r not in gathered:
                    total += WEIGHTS['gather_resource']
                    breakdown[f'gather_resource:{r}'] += WEIGHTS['gather_resource']
                    gathered.add(r)

        if b := R_BUY.search(line):
            code = b.group(1).lower()
            if code in basic and code not in bought:
                total += WEIGHTS['buy_resource']
                breakdown[f'buy_resource:{code}'] += WEIGHTS['buy_resource']
                bought.add(code)

    return total, dict(breakdown)

# ---------------------------------------------------------------------------
#  Ideal (perfect-play) scorer
# ---------------------------------------------------------------------------
def compute_ideal_episode_reward(task: dict) -> tuple[int, dict[str,int]]:
    breakdown = defaultdict(int)
    total     = 0

    # Kill-and-craft
    if task.get('monster_name'):
        boss    = task['monster_name'].lower()
        total  += _add(breakdown, 'target_win')

        missing      = set(task['missing_items'].values())
        intermediate = set()
        basic        = set()

        def _walk2(t: dict):
            c = t['code'].lower()
            if c == 'wooden_stick':
                return
            if 'craft' in t:
                if c not in missing:
                    intermediate.add(c)
                for ing in t['craft']['ingredients']:
                    _walk2(ing)
            else:
                basic.add(c)

        for code in missing:
            _walk2(ct.build_crafting_tree(ct.items_by_code[code]))

        # Decide gatherable vs mob-drop by actual drop mapping
        gatherable = {c for c in basic if not ct.drops_by_item.get(c)}
        mob_drop   = basic - gatherable

        # Map monsters -> codes they drop
        monster_to_codes = defaultdict(set)
        for code in mob_drop:
            for d in ct.drops_by_item.get(code, []):
                monster_to_codes[norm_monster(d['name'])].add(code)

        # Include every monster that can drop a needed item
        for mon in monster_to_codes:
            if mon != boss:
                total += _add(breakdown, f'other_monster:{mon}')

        # Missing equipment
        for code in missing:
            if ct.items_by_code[code].get('craft'):
                total += _add(breakdown, f'craft_missing:{code}')
            else:
                total += _add(breakdown, f'obtain_missing:{code}')
            total += _add(breakdown, f'equip_missing:{code}')

        # Intermediates
        for code in intermediate:
            total += _add(breakdown, f'craft_intermediate:{code}')

        # Gatherable basics
        for code in gatherable:
            total += _add(breakdown, f'gather_resource:{code}')

        return total, dict(breakdown)

    # Pure-craft
    tree   = task['crafting_tree']
    target = tree['code'].lower()
    total += _add(breakdown, 'target_win')

    intermediate = set()
    basic        = set()
    def _walk3(t: dict):
        c = t['code'].lower()
        if 'craft' in t:
            if c != target:
                intermediate.add(c)
            for ing in t['craft']['ingredients']:
                _walk3(ing)
        else:
            basic.add(c)
    _walk3(tree)

    buyable = {
        item['code'].lower()
        for item in task['task_info'].get('Resources', [])
        if item.get('subtype') == 'grand_exchange'
    }
    buyable_basic    = basic & buyable
    gatherable_basic = basic - buyable_basic

    for code in intermediate:
        total += _add(breakdown, f'craft_intermediate:{code}')
    for code in gatherable_basic:
        total += _add(breakdown, f'gather_resource:{code}')
    for code in buyable_basic:
        total += _add(breakdown, f'buy_resource:{code}')

    return total, dict(breakdown)


def _wrap_api(globs, func_name, func):
    def wrapped(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
        except Exception as exc:
            _WORKER_STATE["func_errors"].append({
                "func": func_name,
                "args": repr(args),
                "kwargs": repr(kwargs),
                "error": repr(exc),
            })
            raise
        if isinstance(res, tuple) and len(res) == 2 and isinstance(res[1], dict) and "error" in res[1]:
            err = res[1]["error"]
            _WORKER_STATE["func_errors"].append({
                "func": func_name,
                "args": repr(args),
                "kwargs": repr(kwargs),
                "error_code": err.get("code"),
                "message": err.get("message"),
            })
        return res
    globs[func_name] = wrapped

# per-process storage (created inside child)
_WORKER_STATE = {"func_errors": []}

def _worker(code_str: str, sandbox: dict, q):
    global _WORKER_STATE
    _WORKER_STATE = {"func_errors": []}

    # Build the child's globals from scratch
    g = {"__name__": "__main__"}
    g.update(sandbox or {})

    api = importlib.import_module("Virtual_Environment.api_calls")

    # Wrap only the functions you care about and inject into the child globals
    for name in _API_TO_WRAP:
        if hasattr(api, name):
            fn = getattr(api, name)
            _wrap_api(g, name, fn)   # puts the wrapped fn at g[name]

    stdout, stderr = io.StringIO(), io.StringIO()
    top_trace = None
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            exec(code_str, g, {})
        except Exception:
            top_trace = traceback.format_exc()

    q.put({
        "trace":       top_trace,
        "func_errors": _WORKER_STATE["func_errors"],
        "stdout":      stdout.getvalue(),
        "stderr":      stderr.getvalue(),
    })

def safe_exec(code: str, sandbox: dict | None = None, timeout: float = 5.0):
    ctx = mp.get_context("spawn")           # explicit
    q = ctx.SimpleQueue()                   # simpler than Queue on Windows
    p = ctx.Process(target=_worker, args=(code, sandbox or {}, q), daemon=False)
    p.start()

    try:
        p.join(timeout)
        if p.is_alive():
            p.terminate()
            p.join(2)
            raise TimeoutError(f"Code execution exceeded {timeout} seconds")
        if q.empty():
            return {"trace": None, "func_errors": [], "stdout": "", "stderr": ""}
        run_info = q.get()
        if run_info.get("trace"):
            # Re-raise after capturing
            raise RuntimeError(f"Top-level error:\n{run_info['trace']}")
        return run_info
    finally:
        # Defensive cleanup
        try:
            while not q.empty():
                q.get_nowait()
        except Exception:
            pass
        q.close()

def extract_character_stats(text):
    # Use regex to find the dictionary that starts with {'name': and ends with }
    match = re.search(r"Character Stats:\s*({.*})", text, re.DOTALL)
    
    if match:
        stats_str = match.group(1)

        try:
            # Convert single quotes to double quotes for valid JSON format
            stats_str = stats_str.replace("'", '"')
            
            # Convert string to dictionary safely using json.loads
            character_stats = json.loads(stats_str)

            # Remove 'name' and 'skin' keys if they exist
            character_stats.pop("name", None)
            character_stats.pop("skin", None)

            return character_stats
        except json.JSONDecodeError:
            print("Error parsing character stats.")
            return None
    else:
        print("Character stats not found.")
        return None

def extract_final_code(response: str) -> Optional[str]:
    # 1) Any fenced code block (any language tag or none)
    blocks = re.findall(r'```(?:[\w.+-]+)?\s*\n?([\s\S]*?)```', response)
    if blocks:
        return _strip_angle_wrapping(blocks[-1])

    # 1b) HTML-like <code>...</code> block (sometimes shows up)
    m = re.search(r'<code[^>]*>(.*?)</code>', response, re.IGNORECASE | re.DOTALL)
    if m:
        return _strip_angle_wrapping(m.group(1))

    # 2) No code block → look for "Final answer" marker.
    m = re.search(r'final answer\s*:?\s*(.*)$', response, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    final_part = m.group(1).strip()

    # 3) Try to extract a code block *inside* the final part
    m = re.search(r'```(?:[\w.+-]+)?\s*\n?([\s\S]*?)```', final_part)
    if m:
        return _strip_angle_wrapping(m.group(1))

    # 3b) If the whole final part is wrapped in < ... >, strip that
    m = _ANGLE_WRAP.match(final_part)
    if m:
        return m.group(1).strip()

    # 4) Fallback: assume what's after the marker is plain code
    return final_part

import json
import threading
from typing import Tuple, Optional, Any


class LLMService:
    def __init__(
        self,
        service: str,
        model_name: str,
        api_key: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
        max_tokens: Optional[int] = None,
        streaming: bool = False,
        thinking: bool = False,
        openrouter_referer: Optional[str] = None,
        openrouter_title: Optional[str] = None,
        gigachat_scope: str = "GIGACHAT_API_CORP",
        gigachat_verify_ssl: bool = False,
        system_prompt: str = ""
    ):
        """
        service: 'openai', 'ollama', 'hf', 'openrouter', or 'openrouter_openai'
        """
        self.service = service.lower()
        self.model_name = model_name
        self.streaming = streaming
        self.thinking = thinking
        self.reasoning_effort = reasoning_effort
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

        # Defaults so attributes exist regardless of branch
        self.client = None
        self.tokenizer = None
        self.model = None
        self.openrouter_key = None
        self.openrouter_referer = openrouter_referer
        self.openrouter_title = openrouter_title
        self.giga_client = None

        if self.service == 'openai':
            if not api_key:
                raise ValueError("You must pass an API key for OpenAI")
            try:
                from openai import OpenAI
            except ImportError as e:
                raise ImportError("Install the 'openai' package to use service='openai'") from e
            self.client = OpenAI(api_key=api_key)

        elif self.service in ('openrouter_openai',):
            if not api_key:
                raise ValueError("You must pass an API key for OpenRouter")
            try:
                from openai import OpenAI
            except ImportError as e:
                raise ImportError("Install the 'openai' package to use service='openrouter_openai'") from e
            # OpenAI client pointed at OpenRouter
            self.client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

        elif self.service == 'ollama':
            # no heavy imports here; done in generate()
            pass

        elif self.service.startswith('hf'):
            # Lazy import Transformers + Torch only for HF
            try:
                from transformers import AutoTokenizer, AutoModelForCausalLM
                import torch  # noqa: F401 (device_map uses it)
            except ImportError as e:
                raise ImportError(
                    "Install 'transformers' and 'torch' to use service='hf*'"
                ) from e
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype="auto",
                device_map="auto"
            )

        elif self.service == 'openrouter':
            if not api_key:
                raise ValueError("You must pass an API key for OpenRouter")
            self.openrouter_key = api_key

        elif self.service == 'gigachat':
            if not api_key:
                raise ValueError("You must pass GigaChat credentials")
            try:
                from langchain_gigachat.chat_models import GigaChat
            except ImportError as e:
                raise ImportError(
                    "Install 'langchain-gigachat' to use service='gigachat'"
                ) from e
            # Create client; messages will be constructed in generate()
            self.giga_client = GigaChat(
                model=self.model_name,
                credentials=api_key,
                scope=gigachat_scope,
                verify_ssl_certs=gigachat_verify_ssl,
                max_tokens=self.max_tokens,
                use_api_for_tokens=True,
                timeout=400
            )

        else:
            raise ValueError(f"Unknown service {service!r}")

    def generate(self, data: str) -> Tuple[str, Any, Optional[int], Optional[float]]:
        """
        Returns:
            final_text   – model’s end-user answer
            raw_response – full response incl. reasoning / metadata
            token_count  – number of tokens used (provider-specific)
            cost         – provider-specific cost (if available)
        """
        # ---------- OpenAI ----------
        if self.service == 'openai':
            args = {"model": self.model_name, "input": data}
            if self.model_name.startswith('o'):
                # NOTE: keep both keys if your SDK supports them together.
                # If not, merge as needed.
                args["reasoning"] = {"effort": self.reasoning_effort, "summary": "auto"}
            resp = self.client.responses.create(**args)
            resp_dict = resp.model_dump()
            final_text = resp.output_text
            usage = getattr(resp, "usage", None) or {}
            token_count = getattr(usage, "total_tokens", None) or usage.get("total_tokens")
            return final_text, resp_dict, token_count, None

        # ---------- OpenRouter via OpenAI SDK ----------
        elif self.service in ('openrouter_openai',):
            extra_headers = {}
            if self.openrouter_referer:
                extra_headers["HTTP-Referer"] = self.openrouter_referer
            if self.openrouter_title:
                extra_headers["X-Title"] = self.openrouter_title

            extra_body = {"usage": {"include": True}}
            if self.reasoning_effort:
                extra_body["reasoning"] = {"effort": self.reasoning_effort}

            kwargs = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": data}],
                "extra_body": extra_body,
            }
            if extra_headers:
                kwargs["extra_headers"] = extra_headers
            if self.max_tokens is not None:
                kwargs["max_tokens"] = self.max_tokens

            resp = self.client.chat.completions.create(**kwargs)
            resp_dict = resp.model_dump()
            final_text = resp.choices[0].message.content if resp.choices else ""
            usage = resp_dict.get("usage", {}) or {}
            token_count = usage.get("total_tokens")
            cost = usage.get("cost")
            return final_text, resp_dict, token_count, cost

        # ---------- Ollama ----------
        elif self.service == 'ollama':
            try:
                from ollama import chat as ollama_chat
            except ImportError as e:
                raise ImportError("Install 'ollama' to use service='ollama'") from e
            response = ollama_chat(
                model=self.model_name,
                messages=[{"role": "user", "content": data}]
            )
            final_text = response['message']['content']
            return final_text, response, None, None

        # ---------- Hugging Face (Transformers) ----------
        elif self.service.startswith('hf'):
            try:
                from transformers import TextIteratorStreamer
            except ImportError as e:
                raise ImportError("Install 'transformers' to use service='hf*'") from e

            tok, model = self.tokenizer, self.model
            messages = [{"role": "user", "content": data}]
            text = tok.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=self.thinking
            )
            inputs = tok([text], return_tensors="pt").to(model.device)

            if self.streaming:
                streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True)
                gen_kwargs = dict(
                    **inputs,
                    streamer=streamer,
                    max_new_tokens=32768
                )
                thread = threading.Thread(target=model.generate, kwargs=gen_kwargs)
                thread.start()

                output_text = ""
                token_count = 0
                for token in streamer:
                    print(token, end="", flush=True)
                    output_text += token
                    token_count += 1
                thread.join()
                return output_text, output_text, token_count, None
            else:
                generated = model.generate(
                    **inputs,
                    max_new_tokens=32768
                )
                output_ids = generated[0][len(inputs.input_ids[0]):].tolist()
                token_count = len(output_ids)
                raw_text = tok.decode(output_ids, skip_special_tokens=True)
                # Try to split off any reasoning tokens if your model uses them
                try:
                    split_idx = len(output_ids) - output_ids[::-1].index(151668)
                except ValueError:
                    split_idx = 0
                final_text = tok.decode(output_ids[split_idx:], skip_special_tokens=True).strip()
                return final_text, raw_text, token_count, None

        # ---------- OpenRouter (HTTP) ----------
        elif self.service == 'openrouter':
            try:
                import requests
            except ImportError as e:
                raise ImportError("Install 'requests' to use service='openrouter'") from e

            headers = {"Authorization": f"Bearer {self.openrouter_key}"}
            if self.openrouter_referer:
                headers["HTTP-Referer"] = self.openrouter_referer
            if self.openrouter_title:
                headers["X-Title"] = self.openrouter_title

            if self.model_name.startswith(('google', 'anthropic')) and self.max_tokens is not None:
                payload = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": data}],
                    "usage": {"include": True},
                    "reasoning": {"max_tokens": self.max_tokens}
                }
            else:
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": "Set reasoning effort to high"},
                        {"role": "user", "content": data}
                    ],
                    "usage": {"include": True},
                    "reasoning": {
                        "effort": self.reasoning_effort,
                        "exclude": False,
                        "enabled": True
                    }
                }

            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload)
            )
            result = response.json()
            final_text = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {}) or {}
            return final_text, result, usage.get("completion_tokens"), usage.get("cost")

        # ---------- GigaChat ----------
        elif self.service == 'gigachat':
            try:
                from langchain_core.messages import HumanMessage, SystemMessage
            except ImportError as e:
                raise ImportError(
                    "Install 'langchain-core' (comes with LangChain) to use service='gigachat'"
                ) from e

            msgs = [SystemMessage(self.system_prompt or ""), HumanMessage(content=data)]
            res = self.giga_client(msgs)

            res_dict = {
                "content": getattr(res, "content", None),
                "additional_kwargs": getattr(res, "additional_kwargs", None),
                "response_metadata": getattr(res, "response_metadata", None),
                "usage_metadata": getattr(res, "usage_metadata", None),
                "id": getattr(res, "id", None),
            }

            usage = res_dict.get("usage_metadata") or {}
            if not usage:
                rm = res_dict.get("response_metadata") or {}
                token_usage = rm.get("token_usage") or {}
                usage = {
                    "input_tokens": token_usage.get("prompt_tokens"),
                    "output_tokens": token_usage.get("completion_tokens"),
                    "total_tokens": token_usage.get("total_tokens"),
                    "input_token_details": {"cache_read": token_usage.get("precached_prompt_tokens")},
                    "model_name": rm.get("model_name"),
                    "finish_reason": rm.get("finish_reason"),
                    "x_headers": rm.get("x_headers"),
                }

            output_tokens = (
                usage.get("output_tokens")
                or usage.get("completion_tokens")
                or (usage.get("token_usage", {}) or {}).get("completion_tokens")
            )
            total_tokens = (
                usage.get("total_tokens")
                or (usage.get("token_usage", {}) or {}).get("total_tokens")
            )

            final_text = res_dict["content"] or ""
            return final_text, res_dict, output_tokens, None

        else:
            raise RuntimeError("Unsupported service")


def cut_events_before_creation(data, creation_log='Successfully created custom character - Hero.'):
    """
    Cuts the list of events at the first appearance of the specified creation log.

    Args:
        data (tuple): A tuple where the second element is a list of event dictionaries.
        creation_log (str): The log string to stop at (inclusive). Default is for 'Hero'.

    Returns:
        list: A list of events up to and including the first matching creation log event.
    """
    events = data[1]  # Extract the event list from the tuple
    cut_events = []
    for event in events:
        cut_events.append(event)
        if event.get('log') == creation_log:
            break
    return cut_events

def create_character(name, data):
    delete_character(name)
    char = extract_character_stats(data)
    create_custom_character(name, "men1", char)

def get_task_type(task_string: str) -> str:
    if 'Your task is to craft' in task_string:
        return 'craft'
    elif 'Your task is to kill' in task_string:
        return 'kill'
    else:
        raise ValueError("Unknown task type in string")

def extract_result(logs, prompt, task):
    task_type = get_task_type(prompt)
    if task_type == 'kill':
        target = task.get('monster_name', '').lower()
        # Look for a winning fight against the target monster
        for entry in logs:
            log_txt = entry.get('log', '').lower()
            if entry.get('action_type') == 'fight' and target in log_txt and 'win' in log_txt:
                return 'win'
        return 'lose'

    elif task_type == 'craft':
        target = (task.get('crafting_tree', {}) or {}).get('code', '').lower()
        failed_craft_found = False
        successful_craft_found = False

        for entry in logs:
            log_txt = entry.get('log', '').lower()
            if target in log_txt:
                if 'failed to craft' in log_txt:
                    failed_craft_found = True
                    break
                elif 'crafts' in log_txt or 'crafted' in log_txt:
                    successful_craft_found = True

        if failed_craft_found:
            return 'lose'
        if successful_craft_found:
            return 'win'
        return 'lose'

    else:
        raise ValueError(f"Unknown task_type: {task_type!r}")



def get_tasks_to_run(task_list, string_list, task_num):
    """
    Determines which tasks to run based on the task_num parameter.

    Parameters:
        task_list (list): List of task JSON objects.
        string_list (list): Corresponding list of prompt strings.
        task_num (str or int): 'all', a specific task number (1-based), or a range 'start-end'.

    Returns:
        List of tuples: Each tuple contains (task_index, (task, prompt)).
    """
    if task_num == 'all':
        return list(enumerate(zip(task_list, string_list), start=1))
    elif isinstance(task_num, int) or (isinstance(task_num, str) and task_num.isdigit()):
        n = int(task_num)
        if not (1 <= n <= len(task_list)):
            raise ValueError(f"task_num must be 1–{len(task_list)} or 'all'")
        return [(n, (task_list[n-1], string_list[n-1]))]
    elif isinstance(task_num, str) and '-' in task_num:
        start_str, end_str = task_num.split('-')
        start = int(start_str)
        end = int(end_str)
        if not (1 <= start <= end <= len(task_list)):
            raise ValueError(f"Range must be within 1–{len(task_list)}")
        return list(
            (i, (task_list[i-1], string_list[i-1])) for i in range(start, end+1)
        )
    else:
        raise ValueError(f"Invalid task_num format: {task_num}")
