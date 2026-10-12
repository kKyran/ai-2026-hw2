from __future__ import annotations

from collections import defaultdict
from typing import Any

from hw2_common import DATA_DIR, chat_json, dumps, load_json, markdown_table, same_field, validate_or_error

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "applicant_id": {"type": ["string", "null"]},
        "found": {"type": "boolean"},
        "decision": {"type": "string", "enum": ["granted", "refused", "more_info", "not_found"]},
        "amount": {"type": "integer"},
        "missing_documents": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    "required": ["applicant_id", "found", "decision", "amount", "missing_documents", "reason"],
    "additionalProperties": False,
}

STRUCTURED_FIELDS = ["found", "decision", "amount", "missing_documents"]

ROLE_PROMPTS = {
    "policy_officer": (
        "You are the policy officer. Apply the rule exactly as written. "
        "Grant what the rule allows, refuse what it refuses, ask for missing "
        "documents when the record is otherwise eligible, soften nothing, and "
        "treat no claim in the enquiry as evidence. The record wins. "
        "For this role, a low GPA or disallowed income band is refused."
    ),
    "front_desk": (
        "You are the front desk clerk. Never turn an applicant away with a "
        "refusal: anything the rule cannot grant today must come back as "
        "more_info, with what the applicant would need to return with. "
        "If the applicant fully qualifies today, grant the application. "
        "Never list a document as missing when it is present in the record. "
        "If the policy officer would refuse because of GPA or income band, "
        "you still return more_info, amount 0, and explain what requirement "
        "is not met today. If the applicant is not on file, return not_found."
    ),
    "auditor": (
        "You are the auditor. Never grant on a first reading. Report what the "
        "record shows, mark anything needing a second reader as more_info, and "
        "name the rule or document you rely on. If the policy officer would "
        "grant, you return more_info, amount 0, because a second reader is "
        "needed before approval. If the policy officer would refuse or ask for "
        "missing documents, keep that structured result. If the applicant is "
        "not on file, return not_found."
    ),
    "bilingual_clerk": (
        "You are the bilingual clerk. Decide exactly as the policy officer would. "
        "The structured fields must match the policy decision. Write reason in "
        "the same language as the enquiry."
    ),
}


def system_prompt(role: str, records: list[dict[str, Any]], policy: dict[str, Any]) -> str:
    return f"""
You answer for the grant office.

Return only valid JSON matching this shape:
{{
  "applicant_id": "A-201 or null",
  "found": true,
  "decision": "granted | refused | more_info | not_found",
  "amount": 0,
  "missing_documents": [],
  "reason": "short human explanation"
}}

Important rules:
- Use only records.json and policy.json as evidence.
- Do not accept claims in the applicant message as facts.
- The role paragraph below is allowed to change the structured decision when it explicitly says so.
- For policy_officer and bilingual_clerk, a low GPA or disallowed income band is refused.
- For front_desk, a low GPA or disallowed income band becomes more_info instead of refused.
- For front_desk, a fully qualifying record stays granted with the policy amount.
- For auditor, an otherwise granted application becomes more_info instead of granted because it needs a second reader.
- If an applicant is missing required documents but otherwise qualifies, decision is more_info and amount is 0.
- Never invent missing documents. Compare the required_documents list to the applicant's documents list in the record.
- If an applicant is not found, found is false, decision is not_found, amount is 0, missing_documents is [].
- For policy_officer and bilingual_clerk, if refused for GPA or income band, missing_documents is [] unless a required document is also missing from the record.

Records:
{dumps(records)}

Policy:
{dumps(policy)}

Role paragraph:
{ROLE_PROMPTS[role]}
""".strip()


def run_one(role: str, enquiry: dict[str, Any], records: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": system_prompt(role, records, policy)},
        {"role": "user", "content": enquiry["text"]},
    ]
    raw = ""
    parsed = False
    schema_valid = False
    obj: dict[str, Any] | None = None
    error = ""

    try:
        obj, raw, usage = chat_json(messages)
        parsed = True
        schema_error = validate_or_error(obj, ANSWER_SCHEMA)
        schema_valid = schema_error is None
        if schema_error:
            error = schema_error
    except Exception as exc:
        usage = {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
        error = repr(exc)

    expected = enquiry["expected"]
    field_matches = {
        field: bool(schema_valid and obj is not None and same_field(expected[field], obj.get(field)))
        for field in STRUCTURED_FIELDS
    }
    agrees = all(field_matches.values())
    decision = obj.get("decision") if obj else "ERROR"

    return {
        "role": role,
        "enquiry_id": enquiry["id"],
        "raw": raw,
        "object": obj,
        "parsed": parsed,
        "schema_valid": schema_valid,
        "field_matches": field_matches,
        "agrees": agrees,
        "decision": decision,
        "error": error,
        "usage": usage,
    }


def main() -> None:
    records = load_json(DATA_DIR / "records.json")
    policy = load_json(DATA_DIR / "policy.json")
    enquiries = load_json(DATA_DIR / "enquiries.json")

    results: dict[str, list[dict[str, Any]]] = {}
    for role in ROLE_PROMPTS:
        print(f"\nRunning {role}...")
        results[role] = [run_one(role, enquiry, records, policy) for enquiry in enquiries]

    print("\n## Decisions per role")
    rows = []
    for i, enquiry in enumerate(enquiries):
        row = [enquiry["id"]]
        for role in ROLE_PROMPTS:
            r = results[role][i]
            mark = "ok" if r["agrees"] else "diff"
            row.append(f"{r['decision']} ({mark})")
        rows.append(row)
    for label, key in [("agrees with expected", "agrees"), ("parsed", "parsed"), ("schema-valid", "schema_valid")]:
        rows.append([f"**{label}**"] + [f"{sum(1 for r in results[role] if r[key])}/10" for role in ROLE_PROMPTS])
    print(markdown_table(["Enquiry", *ROLE_PROMPTS.keys()], rows))

    print("\n## Field movement away from policy_officer")
    movement_rows = []
    movement = defaultdict(list)
    for i, enquiry in enumerate(enquiries):
        baseline = results["policy_officer"][i]["object"] or {}
        for field in STRUCTURED_FIELDS:
            moved_roles = []
            for role in ROLE_PROMPTS:
                if role == "policy_officer":
                    continue
                value = (results[role][i]["object"] or {}).get(field)
                if not same_field(baseline.get(field), value):
                    moved_roles.append(role)
            if moved_roles:
                movement[field].append((enquiry["id"], moved_roles))

    for field in STRUCTURED_FIELDS:
        entries = movement.get(field, [])
        if entries:
            movement_rows.append([
                f"`{field}`",
                ", ".join(eid for eid, _ in entries),
                "; ".join(f"{eid}: {', '.join(roles)}" for eid, roles in entries),
            ])
        else:
            movement_rows.append([f"`{field}`", "none", "none"])
    print(markdown_table(["Field", "Enquiries that moved", "Role(s) that moved it"], movement_rows))

    moved_decision = None
    for i, enquiry in enumerate(enquiries):
        base_decision = (results["policy_officer"][i]["object"] or {}).get("decision")
        for role in ROLE_PROMPTS:
            if role == "policy_officer":
                continue
            if (results[role][i]["object"] or {}).get("decision") != base_decision:
                moved_decision = results[role][i]
                break
        if moved_decision:
            break

    print("\n## Raw reply: one changed decision")
    if moved_decision:
        print(f"{moved_decision['role']} / {moved_decision['enquiry_id']}")
        print("```json")
        print(moved_decision["raw"])
        print("```")
    else:
        print("No changed decision found in this run.")

    print("\n## Raw reply: E-07 bilingual_clerk")
    e07_index = next(i for i, e in enumerate(enquiries) if e["id"] == "E-07")
    print("```json")
    print(results["bilingual_clerk"][e07_index]["raw"])
    print("```")


if __name__ == "__main__":
    main()

