from __future__ import annotations

from pathlib import Path
from typing import Any

from hw2_common import DATA_DIR, chat_json, chat_text, dumps, load_json, markdown_table, validate_or_error

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_id": {"type": "string"},
        "story_file": {"type": "string"},
        "full_name": {"type": ["string", "null"]},
        "degree": {"type": ["string", "null"]},
        "graduation_year": {"type": ["integer", "null"]},
        "gpa_4_scale": {"type": ["number", "null"]},
        "gpa_original": {"type": ["string", "null"]},
        "languages": {"type": "array", "items": {"type": "string"}},
        "published_peer_reviewed_outputs": {"type": "integer", "minimum": 0},
        "unpublished_outputs": {"type": "array", "items": {"type": "string"}},
        "total_countable_experience_months": {"type": ["integer", "null"], "minimum": 0},
        "evidence": {"type": "object"},
        "ambiguities": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": [
        "candidate_id",
        "story_file",
        "full_name",
        "degree",
        "graduation_year",
        "gpa_4_scale",
        "gpa_original",
        "languages",
        "published_peer_reviewed_outputs",
        "unpublished_outputs",
        "total_countable_experience_months",
        "evidence",
        "ambiguities",
        "notes",
    ],
    "additionalProperties": False,
}

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_id": {"type": "string"},
        "scores": {
            "type": "object",
            "properties": {
                "academic": {"type": "number", "minimum": 0, "maximum": 5},
                "research": {"type": "number", "minimum": 0, "maximum": 5},
                "experience": {"type": "number", "minimum": 0, "maximum": 5},
            },
            "required": ["academic", "research", "experience"],
            "additionalProperties": False,
        },
        "notes": {"type": "string"},
    },
    "required": ["candidate_id", "scores", "notes"],
    "additionalProperties": False,
}


def extraction_prompt(story_file: str, candidate_id: str) -> str:
    return f"""
Extract a structured CV from {story_file}. Return only JSON.

Required extraction rules:
- A fact the story does not state is null. Never estimate. No GPA means no GPA.
- A GPA on another scale is converted to a 4.0 scale, and the original scale is recorded beside it.
- A paper is published only when the story says published or accepted.
- Submitted, under review, in preparation, planned, and in press are not published; record them separately and do not count them.
- Contradictions are not resolved and not averaged: the field is null, and the contradiction is recorded in ambiguities.
- Count experience in months. Overlapping periods count once. A period with no dates is not countable.
- For every filled field, include a short evidence quote in evidence.

Return this exact JSON shape:
{{
  "candidate_id": "{candidate_id}",
  "story_file": "{story_file}",
  "full_name": null,
  "degree": null,
  "graduation_year": null,
  "gpa_4_scale": null,
  "gpa_original": null,
  "languages": [],
  "published_peer_reviewed_outputs": 0,
  "unpublished_outputs": [],
  "total_countable_experience_months": null,
  "evidence": {{}},
  "ambiguities": [],
  "notes": ""
}}
""".strip()


def repair_prompt(schema: dict[str, Any], error: str) -> str:
    return f"""
Repair the JSON so it validates against this schema. Return only the repaired JSON.
Do not add new facts. Keep null when a fact is missing or contradicted.

Validation error:
{error}

Schema:
{dumps(schema)}
""".strip()


def extract_cv(path: Path) -> dict[str, Any]:
    story = path.read_text(encoding="utf-8")
    messages = [
        {"role": "system", "content": extraction_prompt(path.name, path.stem)},
        {"role": "user", "content": story},
    ]
    result = {"story_file": path.name, "parsed": False, "valid": False, "raw": "", "object": None, "error": ""}
    try:
        obj, raw, usage = chat_json(messages)
        obj["candidate_id"] = path.stem
        obj["story_file"] = path.name
        result.update({"parsed": True, "raw": raw, "object": obj, "usage": usage})
        error = validate_or_error(obj, EXTRACTION_SCHEMA)
        if error:
            repair_messages = [
                {"role": "system", "content": repair_prompt(EXTRACTION_SCHEMA, error)},
                {"role": "user", "content": dumps(obj)},
            ]
            repaired, repaired_raw, repair_usage = chat_json(repair_messages)
            repaired["candidate_id"] = path.stem
            repaired["story_file"] = path.name
            repaired_error = validate_or_error(repaired, EXTRACTION_SCHEMA)
            if repaired_error is None:
                obj = repaired
                raw = repaired_raw
                usage = repair_usage
                error = None
                result.update({"raw": raw, "object": obj, "usage": usage})
        result["valid"] = error is None
        result["error"] = error or ""
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def score_prompt(rubric: Any) -> str:
    return f"""
Score the candidate against the rubric. Return only JSON.

Rules:
- Return a 0-5 score for academic, research, and experience.
- Do not compute a weighted total.
- Use only the extracted CV fields and the rubric.
- If a required field is null because it was missing or contradicted, score from the usable evidence only.

Rubric:
{dumps(rubric)}

Return this JSON shape:
{{
  "candidate_id": "story-01",
  "scores": {{
    "academic": 0,
    "research": 0,
    "experience": 0
  }},
  "notes": ""
}}
""".strip()


def score_cv(cv: dict[str, Any], rubric: Any) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": score_prompt(rubric)},
        {"role": "user", "content": dumps(cv)},
    ]
    result = {"candidate_id": cv["candidate_id"], "parsed": False, "valid": False, "raw": "", "object": None, "error": ""}
    try:
        obj, raw, usage = chat_json(messages)
        obj["candidate_id"] = cv["candidate_id"]
        result.update({"parsed": True, "raw": raw, "object": obj, "usage": usage})
        error = validate_or_error(obj, SCORE_SCHEMA)
        result["valid"] = error is None
        result["error"] = error or ""
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def weighted_total(scores: dict[str, float], rubric: Any) -> float:
    weights = {criterion["id"]: criterion["weight"] for criterion in rubric["criteria"]}
    total = sum(float(scores[key]) * weights[key] for key in weights)
    return round(total, 2)


def null_fields(cv: dict[str, Any]) -> list[str]:
    tracked = ["full_name", "degree", "graduation_year", "gpa_4_scale", "gpa_original", "total_countable_experience_months"]
    return [field for field in tracked if cv.get(field) is None]


def traps(cv: dict[str, Any]) -> list[str]:
    hits = []
    if cv.get("gpa_4_scale") is None:
        hits.append("no GPA stated or contradicted")
    original = str(cv.get("gpa_original") or "").lower()
    if "5" in original and "4.0" not in original:
        hits.append("GPA on another scale")
    if cv.get("unpublished_outputs"):
        hits.append("paper not published")
    if cv.get("ambiguities"):
        hits.append("contradiction")
    return hits


def prose_winner(cvs: list[dict[str, Any]], rubric: Any) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are advising the scholarship committee in prose. "
                "Using the extracted CVs and rubric, say who should win and why. "
                "This is a separate prose judgement; do not output JSON."
            ),
        },
        {"role": "user", "content": "Rubric:\n" + dumps(rubric) + "\n\nExtracted CVs:\n" + dumps(cvs)},
    ]
    text, _usage = chat_text(messages)
    return text


def main() -> None:
    rubric = load_json(DATA_DIR / "candidate_rubric.json")
    story_paths = sorted((DATA_DIR / "candidates").glob("story-*.md"))

    extraction_results = []
    cvs = []
    for path in story_paths:
        print(f"\nExtracting {path.name}...")
        result = extract_cv(path)
        extraction_results.append(result)
        if result["parsed"] and result["object"]:
            cvs.append(result["object"])

    print("\n## Part 1 - extraction")
    extraction_rows = []
    for result in extraction_results:
        cv = result["object"] or {}
        extraction_rows.append([
            result["story_file"].replace(".md", ""),
            "yes" if result["parsed"] else "no",
            "yes" if result["valid"] else "no",
            ", ".join(null_fields(cv)) if cv else result["error"],
            ", ".join(traps(cv)) if cv else "",
        ])
    print(markdown_table(["Story", "Parsed?", "Valid?", "Fields that came back null", "Traps hit"], extraction_rows))

    story_06 = next((r for r in extraction_results if r["story_file"] == "story-06.md"), None)
    print("\n## Extraction for story-06")
    print("```json")
    print(dumps(story_06["object"] if story_06 else None))
    print("```")

    score_results = []
    ranking_rows = []
    for cv in cvs:
        print(f"\nScoring {cv['candidate_id']}...")
        score = score_cv(cv, rubric)
        score_results.append(score)
        if score["valid"]:
            scores = score["object"]["scores"]
            total = weighted_total(scores, rubric)
            ranking_rows.append([
                cv["candidate_id"],
                scores["academic"],
                scores["research"],
                scores["experience"],
                total,
            ])

    ranking_rows.sort(key=lambda row: row[4], reverse=True)
    print("\n## Part 2 - scores and computed winner")
    print(markdown_table(["Candidate", "academic", "research", "experience", "weighted total (code)"], ranking_rows))

    winner = ranking_rows[0][0] if ranking_rows else "none"
    print(f"\nWinner, computed by code: {winner}")

    print("\n## Model prose answer, asked separately")
    print(prose_winner(cvs, rubric))


if __name__ == "__main__":
    main()

