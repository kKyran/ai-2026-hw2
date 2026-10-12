from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from jsonschema import ValidationError, validate
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")


def load_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def client() -> OpenAI:
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and add your key."
        )
    return OpenAI()


def extract_json(text: str) -> Any:
    stripped = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, flags=re.S)
    if fenced:
        stripped = fenced.group(1).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        first_obj = stripped.find("{")
        first_arr = stripped.find("[")
        starts = [i for i in [first_obj, first_arr] if i != -1]
        if not starts:
            raise
        start = min(starts)
        end = max(stripped.rfind("}"), stripped.rfind("]"))
        if end <= start:
            raise
        return json.loads(stripped[start : end + 1])


def chat_text(messages: list[dict[str, str]]) -> tuple[str, dict[str, int | None]]:
    response = client().chat.completions.create(
        model=MODEL,
        messages=messages,
    )
    text = response.choices[0].message.content or ""
    return text, usage_dict(response)


def chat_json(messages: list[dict[str, str]]) -> tuple[Any, str, dict[str, int | None]]:
    response = client().chat.completions.create(
        model=MODEL,
        messages=messages,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or ""
    return extract_json(raw), raw, usage_dict(response)


def usage_dict(response: Any) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def validate_or_error(obj: Any, schema: dict[str, Any]) -> str | None:
    try:
        validate(instance=obj, schema=schema)
        return None
    except ValidationError as exc:
        return exc.message


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        text = "" if value is None else str(value)
        return text.replace("\n", "<br>").replace("|", "\\|")

    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(cell(v) for v in row) + " |")
    return "\n".join(out)


def same_field(expected: Any, got: Any) -> bool:
    if isinstance(expected, list) and isinstance(got, list):
        return sorted(expected) == sorted(got)
    return expected == got

