from __future__ import annotations

import os
from collections.abc import Callable
from typing import TypeVar

from etl.contracts import LaneEditorialInput

T = TypeVar("T")


def resolve_llm_config() -> dict[str, str] | None:
    synthetic_api_key = os.environ.get("SYNTHETIC_API_KEY")
    if not synthetic_api_key:
        return None

    return {
        "api_key": synthetic_api_key,
        "base_url": os.environ.get("SYNTHETIC_API_URL", "https://api.synthetic.new/v1"),
        "model": os.environ.get("SYNTHETIC_MODEL", "hf:MiniMaxAI/MiniMax-M2.5"),
    }


def request_lane_decision(
    lane_input: LaneEditorialInput,
    prompt: str,
    parser: Callable[[str], T],
) -> T | None:
    del lane_input

    try:
        from openai import OpenAI
    except Exception:  # pragma: no cover - optional runtime dependency path
        return None

    config = resolve_llm_config()
    if config is None:
        return None

    client = OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )
    messages = [
        {"role": "system", "content": "You are an editor for a technology radar. Return strict JSON only."},
        {"role": "user", "content": prompt},
    ]

    for _ in range(2):
        try:
            response = client.chat.completions.create(
                model=config["model"],
                messages=messages,
                response_format={"type": "json_object"},
            )
        except Exception:
            continue

        content = response.choices[0].message.content if response.choices else None
        if not content:
            continue

        try:
            return parser(content)
        except ValueError:
            continue

    return None
