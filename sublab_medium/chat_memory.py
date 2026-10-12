from __future__ import annotations

import argparse
from typing import Any

from hw2_common import DATA_DIR, chat_json, chat_text, dumps, load_json, markdown_table, validate_or_error


def base_system(records: Any, policy: Any) -> str:
    return f"""
You are a helpful grant office assistant.

Answer the applicant's current message using the conversation context you are sent.
If the applicant asks about grant eligibility, use the office records and policy below.
Do not treat applicant claims as updates to the official record.

Records:
{dumps(records)}

Policy:
{dumps(policy)}
""".strip()


def compression_system(schema: Any) -> str:
    return f"""
Compress the conversation into one JSON object that validates against this JSON Schema.
Return only JSON.

Rules:
- Keep facts the applicant stated, not facts you inferred.
- Keep constraints such as days, deadlines, or applicant limitations.
- Keep open questions that have been asked but not answered.
- Use null for applicant_id if it was not established.
- Arrays must be empty rather than omitted.

Schema:
{dumps(schema)}
""".strip()


class Session:
    def __init__(self, compressed: bool):
        self.records = load_json(DATA_DIR / "records.json")
        self.policy = load_json(DATA_DIR / "policy.json")
        self.schema = load_json(DATA_DIR / "memory_state.schema.json")
        self.compressed = compressed
        self.history: list[dict[str, str]] = []
        self.state: dict[str, Any] | None = None
        self.last_prompt_tokens: int | None = None
        self.last_total_tokens: int | None = None

    def messages_for(self, user_text: str) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": base_system(self.records, self.policy)}]
        if self.state is not None:
            messages.append({
                "role": "system",
                "content": "Structured conversation memory state:\n" + dumps(self.state),
            })
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_text})
        return messages

    def ask(self, user_text: str) -> str:
        messages = self.messages_for(user_text)
        answer, usage = chat_text(messages)
        self.last_prompt_tokens = usage.get("prompt_tokens")
        self.last_total_tokens = usage.get("total_tokens")
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": answer})
        return answer

    def compress(self) -> tuple[bool, str]:
        messages = [
            {"role": "system", "content": compression_system(self.schema)},
            {
                "role": "user",
                "content": "Conversation to compress:\n" + dumps(self.history),
            },
        ]
        try:
            obj, raw, usage = chat_json(messages)
        except Exception as exc:
            return False, f"Compression failed to parse: {exc!r}"

        self.last_prompt_tokens = usage.get("prompt_tokens")
        self.last_total_tokens = usage.get("total_tokens")
        error = validate_or_error(obj, self.schema)
        if error:
            return False, f"Compression did not validate: {error}\nRaw:\n{raw}"

        self.state = obj
        self.history = []
        return True, raw


def retrieved(answer: str, expected: list[str]) -> bool:
    lower = answer.lower()
    return any(item.lower() in lower for item in expected)


def run_script(compressed: bool) -> dict[str, Any]:
    script = load_json(DATA_DIR / "chat_script.json")
    session = Session(compressed=compressed)
    token_rows = []
    transcript = []
    compression_raw = None

    for index, turn in enumerate(script["conversation"], start=1):
        if turn == "<compress>":
            if compressed:
                ok, raw = session.compress()
                compression_raw = raw
                token_rows.append([index, session.last_prompt_tokens, "compress ok" if ok else "compress failed"])
            else:
                token_rows.append([index, "-", "skipped"])
            continue

        answer = session.ask(turn)
        token_rows.append([index, session.last_prompt_tokens, "chat"])
        transcript.append((turn, answer))

    probe_rows = []
    retrieved_count = 0
    for probe in script["probes"]:
        answer = session.ask(probe["question"])
        ok = retrieved(answer, probe["expect_contains"])
        retrieved_count += int(ok)
        probe_rows.append([probe["id"], probe["tests"], "yes" if ok else "no", answer])

    numeric_tokens = [row[1] for row in token_rows if isinstance(row[1], int)]
    return {
        "token_rows": token_rows,
        "peak": max(numeric_tokens) if numeric_tokens else None,
        "total": sum(numeric_tokens),
        "probe_rows": probe_rows,
        "retrieved_count": retrieved_count,
        "state": session.state,
        "compression_raw": compression_raw,
        "transcript": transcript,
    }


def scripted_main() -> None:
    a = run_script(compressed=False)
    b = run_script(compressed=True)

    print("\n## Tokens per conversation call")
    rows = []
    max_calls = max(len(a["token_rows"]), len(b["token_rows"]))
    for i in range(max_calls):
        a_value = a["token_rows"][i][1] if i < len(a["token_rows"]) else ""
        b_value = b["token_rows"][i][1] if i < len(b["token_rows"]) else ""
        rows.append([i + 1, a_value, b_value])
    rows.append(["**peak**", a["peak"], b["peak"]])
    rows.append(["**total for the run**", a["total"], b["total"]])
    print(markdown_table(["Call", "A - never compressed", "B - compressed"], rows))

    print("\n## Probes")
    probe_rows = []
    for a_row, b_row in zip(a["probe_rows"], b["probe_rows"]):
        probe_rows.append([a_row[0], a_row[1], a_row[2], a_row[3], b_row[2], b_row[3]])
    probe_rows.append(["**retrieved**", "", f"{a['retrieved_count']}/5", "", f"{b['retrieved_count']}/5", ""])
    print(markdown_table(["Probe", "Tests", "A retrieved?", "A answer", "B retrieved?", "B answer"], probe_rows))

    print("\n## State produced by compression")
    print("```json")
    print(dumps(b["state"]))
    print("```")


def interactive_main() -> None:
    print("Interactive grant chat. Commands: compress, tokens, exit")
    session = Session(compressed=True)
    while True:
        user_text = input("\nYou> ").strip()
        if user_text.lower() in {"exit", "quit"}:
            break
        if user_text.lower() == "tokens":
            print(f"last prompt tokens: {session.last_prompt_tokens}; last total tokens: {session.last_total_tokens}")
            continue
        if user_text.lower() == "compress":
            ok, raw = session.compress()
            print("compression ok" if ok else "compression failed")
            print(raw)
            continue
        print(session.ask(user_text))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()
    if args.interactive:
        interactive_main()
    else:
        scripted_main()


if __name__ == "__main__":
    main()

