"""
LLM factory — returns either a local Ollama model or Claude Sonnet 4.6.

Set LLM_PROVIDER=ollama in your .env (or environment) to use Ollama.
Optionally set OLLAMA_MODEL (default: llama3:latest) and OLLAMA_BASE_URL
(default: http://localhost:11434).

Leave LLM_PROVIDER unset (or set to "anthropic") to use Claude.
"""

import os
import re
import json


def get_llm(temperature: float = 0.1, json_mode: bool = False):
    """Return the configured LLM.

    json_mode=True enables Ollama's grammar-constrained JSON output
    (ignored for Anthropic — Claude follows JSON prompts natively).
    Do NOT pass json_mode=True to LLMs used for tool-calling agents.
    """
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        kwargs = dict(
            model=os.getenv("OLLAMA_MODEL", "llama3:latest"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=temperature,
            num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "32768")),
        )
        if json_mode:
            kwargs["format"] = "json"
        return ChatOllama(**kwargs)

    # Default: Anthropic Claude
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        temperature=temperature,
    )


def robust_parse_json(text: str, default=None):
    """
    Parse JSON from an LLM response robustly.
    Handles: empty responses, markdown fences, explanatory preamble,
    single-key wrapper objects (e.g. {"triggers": [...]} when a list is expected),
    and partial JSON surrounded by prose (common with smaller local models).
    Returns `default` if nothing valid can be extracted.
    """
    if not text or not text.strip():
        return default

    text = text.strip()

    # 1. Strip markdown code fences
    if "```" in text:
        for part in text.split("```"):
            part = part.strip().lstrip("json").lstrip("JSON").strip()
            if part.startswith(("{", "[")):
                text = part
                break

    # 2. Try direct parse
    parsed = None
    try:
        parsed = json.loads(text)
    except Exception:
        pass

    # 3. If direct parse failed, find first { ... } or [ ... ] block
    if parsed is None:
        for pattern in (
            r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}',   # shallow object
            r'\[(?:[^\[\]]|(?:\[[^\[\]]*\]))*\]', # shallow array
            r'\{.*\}',   # greedy object fallback
            r'\[.*\]',   # greedy array fallback
        ):
            m = re.search(pattern, text, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group())
                    break
                except Exception:
                    continue

    if parsed is None:
        return default

    # 4. Unwrap single-key objects when the caller expects a list.
    #    e.g. llama3 returns {"triggers": [...]} instead of [...]
    if isinstance(default, list) and isinstance(parsed, dict) and len(parsed) == 1:
        only_val = next(iter(parsed.values()))
        if isinstance(only_val, list):
            return only_val

    return parsed
