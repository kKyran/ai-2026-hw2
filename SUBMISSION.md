# HW2 submission

**Name:** Kyzyrgeldi Kyran
**Student ID:** S23068969
**Group:** CSS4007-ENG-8
**Repository:** https://github.com/kKyran/ai-2026-hw2

## AI tool disclosure

> I used Codex to help write starter Python code, debug the role prompts and schema handling, and explain where to place the run results. I ran the programs myself and used my own outputs for the tables and analysis.

---

## Sublab Easy — one task, four roles

### Decisions per role

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | granted (ok) | granted (ok) | more_info (diff) | granted (ok) |
| E-02 | more_info (ok) | more_info (ok) | more_info (ok) | more_info (ok) |
| E-03 | refused (ok) | more_info (diff) | refused (ok) | refused (ok) |
| E-04 | refused (ok) | more_info (diff) | refused (ok) | refused (ok) |
| E-05 | granted (ok) | granted (ok) | more_info (diff) | granted (ok) |
| E-06 | granted (ok) | granted (ok) | more_info (diff) | granted (ok) |
| E-07 | granted (ok) | granted (ok) | more_info (diff) | granted (ok) |
| E-08 | not_found (ok) | not_found (ok) | not_found (ok) | not_found (ok) |
| E-09 | refused (ok) | more_info (diff) | refused (ok) | refused (ok) |
| E-10 | more_info (ok) | more_info (ok) | more_info (ok) | more_info (ok) |
| **agrees with `expected`** | 10/10 | 7/10 | 6/10 | 10/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

### Which field moved, on which enquiry, under which role

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` | none | none |
| `decision` | E-01, E-03, E-04, E-05, E-06, E-07, E-09 | E-01: auditor; E-03: front_desk; E-04: front_desk; E-05: auditor; E-06: auditor; E-07: auditor; E-09: front_desk |
| `amount` | E-01, E-05, E-06, E-07 | E-01: auditor; E-05: auditor; E-06: auditor; E-07: auditor |
| `missing_documents` | none | none |

### Raw replies

Paste the full reply for **one enquiry where a role changed the decision** away
from the policy officer's:

```json
{
  "applicant_id": "A-201",
  "found": true,
  "decision": "more_info",
  "amount": 0,
  "missing_documents": [],
  "reason": "The record shows GPA 3.4, income band 1, and both required documents, satisfying the policy. A second reader is required before approval under the auditor role."
}
```

Paste the full reply for **E-07 (the Kazakh enquiry)** from the bilingual
clerk, so the `reason` language is visible:

```json
{
  "applicant_id": "A-201",
  "found": true,
  "decision": "granted",
  "amount": 250000,
  "missing_documents": [],
  "reason": "Сіздің GPA көрсеткіші 2.67-ден жоғары, табыс санатыңыз рұқсат етілген және қажетті құжаттардың екеуі де бар. Сізге 250000 теңге грант беріледі."
}
```

### Written answers

**1. Which fields are role-sensitive and which are not?** Point at rows in your
tables.

> In my run, `decision` and `amount` were role-sensitive. `decision` moved on E-01, E-03, E-04, E-05, E-06, E-07, and E-09. `amount` moved on E-01, E-05, E-06, and E-07 because the auditor changed granted cases to `more_info` with amount 0. `found` and `missing_documents` did not move on any enquiry. The `bilingual_clerk` did not move the structured fields; it changed only the language of `reason`.

**2. Which enquiries are most sensitive to the role, and why those?** Say what
E-03, E-04, E-07 and E-10 are each testing.

> E-03 and E-09 are sensitive because the applicant has a low GPA, so the policy officer refuses but the front desk softens this to `more_info`. E-04 is sensitive because the income band is not allowed, so it is also refused by policy but softened by the front desk. E-07 tests the Kazakh enquiry and shows that the bilingual clerk can keep the same decision while changing the reason language; the auditor also changes the granted decision to `more_info`. E-10 tests whether the model accepts the applicant's claim that a document was uploaded. In my run it kept the record as the source of truth, so the missing `id_card` remained.

**3. Where does discretion belong — the role paragraph, or code that reads
`decision` afterwards?** Say what a downstream program can and cannot tell
about which role produced a record.

> Discretion can be described in the role paragraph for the experiment, but important decisions should be enforced in code after reading `decision`. A downstream program can see that a record says `more_info`, `granted`, or `refused`, but without role metadata it cannot reliably know whether `more_info` came from a front desk softening, an auditor second-reader rule, or the policy itself. If the decision is expensive, the program should apply deterministic rule checks instead of trusting the role paragraph.

**4. Is a role a boundary?** Say in Week 2 terms what the role paragraph is
made of, and what you would put in code — not in the prompt — if a wrong
`decision` were expensive.

> A role is not a security boundary. In Week 2 terms, the role paragraph is still just tokens in the context that influence the continuation. It can guide the model, but it cannot guarantee behavior. If a wrong `decision` were expensive, I would put schema validation, deterministic policy checks, allowed decision transitions, logging, and possibly human review in code rather than relying only on the prompt.

---

## Sublab Medium — memory you choose

### Tokens per call

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---|---|
| 1 | 829 | 829 |
| 2 | 910 | 894 |
| 3 | 1025 | 992 |
| 4 | 1132 | 1087 |
| 5 | 1186 | 1145 |
| 6 | 1302 | 1255 |
| 7 | 1385 | 1340 |
| 8 | 1516 | 1450 |
| 9 | 1610 | 1544 |
| 10 | - | 1493 |
| 11 | 1724 | 1033 |
| 12 | 1807 | 1132 |
| **peak** | 1807 | 1544 |
| **total for the run** | 14426 | 14194 |

### Probes after the conversation

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | yes | You are **Daniyar Qoshan**, applicant **A-202**. | yes | You are **Daniyar Qoshan**, applicant **A-202**. |
| Q-2 missing document | turn 5 | yes | Your **ID card** is still missing from the official file. Your transcript is already on record. | yes | Your **ID card** is still missing from your file. |
| Q-3 band and amount | turns 3–4 | yes | Your official income band is **2**, which corresponds to a grant amount of **150,000 KZT**, provided your missing ID card is submitted and recorded. | yes | Your recorded income band is **2**, which corresponds to a grant amount of **150,000 KZT**. |
| Q-4 the constraint | turn 6 | yes | You said you can come to the office on **Thursdays**. The available policy does not provide official office hours or submission days, so please confirm that Thursday submissions are accepted with the office. | yes | You can come to the office on **Thursdays**. |
| Q-5 the open question | turn 7 | yes | You asked whether a **scanned letter from your employer** would count, or whether the **original** was required. | yes | You asked whether a **scanned employer letter is accepted** or whether the **original is required**. |
| **retrieved** | | 5/5 | | 5/5 | |

### The state my compression produced

```json
{
  "applicant_id": "A-202",
  "topic": "2026 need-based study grant application",
  "facts": [
    "The applicant's name is Daniyar Qoshan.",
    "The applicant sent their transcript last week.",
    "The applicant's family certificate says their income band is 2.",
    "The applicant could not upload their ID card because the scanner at home broke.",
    "The applicant has a sister named Aruzhan who applied last year and is also on file."
  ],
  "decisions": [],
  "constraints": [
    "The applicant can only come to the office on Thursdays.",
    "The applicant has lab all week on other days."
  ],
  "open_questions": [
    "Whether a scanned employer letter is accepted or the original is required.",
    "Whether the grant decision will be made the same day if the applicant brings the ID card on Thursday."
  ],
  "language": "English and Kazakh"
}
```

### Written answers

**1. What did compression buy?** Peak tokens both ways, probes retrieved both
ways, and — if a probe was lost — which one and which turn it came from.

> Compression reduced the peak prompt tokens from 1807 to 1544. The total prompt tokens were close in this short run: 14426 without compression and 14194 with compression. Both runs retrieved 5/5 probes, so no probe was lost in my run. The main benefit was that after the compression point the compressed run sent a smaller context again.

**2. Why must the state be structured rather than a paragraph?** You could have
asked for "a summary". Say what changes when the summary is an object with
named fields.

> A structured state can be validated and read by code. The program can check that `applicant_id`, `facts`, `constraints`, and `open_questions` exist and have the right types. A paragraph summary might sound good but the program cannot reliably tell whether it kept the open question, the Thursday constraint, or the applicant id.

**3. What is missing from your state that you would add?** Name what you would
add and what you would drop to pay for it.

> I would add a field for `related_people` or `other_applicants_mentioned`, because Aruzhan appears in the conversation and could be confused with the current applicant later. To pay for it, I would shorten the free text in `facts`, for example replacing full sentences with shorter facts like `income_band_claimed: 2` and `missing_upload_reason: broken scanner`.

**4. When is compression the wrong choice?** Name a conversation where it would
lose something that cannot be recovered, and say whether your program would
notice.

> Compression is the wrong choice when exact wording matters, such as a legal complaint, medical consent conversation, or audit transcript. A summary can keep the meaning but lose the exact words, uncertainty, or tone. My program would notice only malformed or schema-invalid state; it would not automatically notice that an important phrase was summarized away.

---

## Sublab Hard — stories in, CVs out, the best candidate by code

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back `null` | Traps hit |
|---|---|---|---|---|
| story-01 | yes | yes | | |
| story-02 | yes | yes | graduation_year, gpa_4_scale, gpa_original | no GPA stated or contradicted, paper not published, contradiction |
| story-03 | yes | yes | | GPA on another scale, paper not published |
| story-04 | yes | yes | | paper not published |
| story-05 | yes | yes | | paper not published |
| story-06 | yes | yes | graduation_year, gpa_4_scale, gpa_original | no GPA stated or contradicted, paper not published, contradiction |

The four traps, for reference: no GPA stated · a GPA on another scale · a paper
that is not published · a story that contradicts itself.

Paste the extraction for **story-06**, the one that contradicts itself:

```json
{
  "candidate_id": "story-06",
  "story_file": "story-06.md",
  "full_name": "Nurzhan Abilov",
  "degree": "BSc in Statistics",
  "graduation_year": null,
  "gpa_4_scale": null,
  "gpa_original": null,
  "languages": [
    "Kazakh",
    "Russian",
    "English"
  ],
  "published_peer_reviewed_outputs": 1,
  "unpublished_outputs": [
    "Poster at a local event"
  ],
  "total_countable_experience_months": 40,
  "evidence": {
    "full_name": "\"# Nurzhan Abilov\"",
    "degree": "\"I graduated in 2024 with a BSc in Statistics.\"",
    "languages": "\"Languages: Kazakh, Russian, English.\"",
    "published_peer_reviewed_outputs": "\"one paper published, in a peer-reviewed proceedings, on survey weighting.\"",
    "unpublished_outputs": "\"One poster at a local event, which I do not think counts.\"",
    "total_countable_experience_months": "\"I have been at an insurance analytics team since February 2023, which is about forty months.\""
  },
  "ambiguities": [
    "Graduation status and year are contradictory: the story says \"I graduated in 2024\" and also says \"I am currently a final-year student graduating in 2026.\"",
    "GPA is contradictory: the story gives both 3.2 and 3.5 and says the value is uncertain; no GPA was recorded.",
    "The stated experience duration is approximate (\"about forty months\"); 40 months was recorded as the supplied count."
  ],
  "notes": ""
}
```

### Part 2 — scores and the winner

| Candidate | academic (0–5) | research (0–5) | experience (0–5) | weighted total (code) |
|---|---|---|---|---|
| story-01 | 5 | 5 | 2 | 4.4 |
| story-02 | 1 | 2.5 | 5 | 2.25 |
| story-03 | 4 | 3 | 3 | 3.5 |
| story-04 | 4 | 3 | 5 | 3.9 |
| story-05 | 5 | 2.5 | 1.25 | 3.5 |
| story-06 | 1 | 3 | 5 | 2.4 |

**Winner, computed by my code:** story-01

**The model's prose answer, asked separately ("who should win?"):**

> Aziza Bekova should receive the scholarship.
>
> She has the strongest academic record among the six candidates: a clearly stated BSc in Computer Science and a 3.8 GPA on a 4.0 scale, meeting the rubric's top academic threshold. She also has two published peer-reviewed outputs, which is the highest research record in the shortlist. Although her directly relevant experience is comparatively modest at eight documented months, the academic criterion carries half of the total weighting and research carries a further 30%, making her combination particularly strong.
>
> Aisha Нұрланқызы is the closest alternative academically, with a 3.9 GPA, but has only one published paper and six months of experience. Lyazzat Omarova has a solid record but a converted GPA of 3.68, one published output, and 14 months of experience. Tamerlan Saparov has 24 months of experience, but his GPA is 3.6 and only one output is published; the remaining papers cannot be counted because they are under review or in preparation. Dias Yerzhanov and Nurzhan Abilov have substantial experience, but neither provides a usable GPA, which is a major disadvantage under the heavily weighted academic criterion.
>
> On the evidence available and applying the counting rules strictly, Aziza offers the best balance of academic excellence and demonstrated research achievement, and should be ranked first.

### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it?** Name the
story that forced it.

> The most important rule was that contradictions are not resolved or averaged. Story-06 forced this rule because it gives two GPA values, 3.2 and 3.5, and also says both that the candidate graduated in 2024 and is currently graduating in 2026. Without the rule, the model could choose one number or average them, which would make the structured CV look more certain than the story is.

**2. Where did the model guess, and where did your code have to decide?** One
example of each, from your run.

> The model guessed or normalized the phrase "about forty months" in story-06 into 40 months. My code had to decide the weighted total and winner from the returned scores. For example, story-01 received 5 academic, 5 research, and 2 experience, and the code computed 4.4 and selected story-01 as winner.

**3. Did your prose ranking and your computed ranking agree?** Say which one
you trust and why — and if they agreed, what you would need to see before
trusting the prose one alone.

> They agreed: both the computed ranking and the separate prose answer selected Aziza Bekova / story-01. I still trust the computed ranking more because it uses structured scores and a visible formula. Before trusting the prose answer alone, I would need to see that it used the same extracted fields, counted publications the same way, and did not silently change the weighting.

**4. The rubric has no anchor for a contradicted field.** The stories say 3.2
and then 3.5; the rubric defines a 0 and a 5 and nothing in between for this
case. Say what you did and what the rule should be.

> I set the contradicted GPA fields to `null` and recorded the contradiction in `ambiguities`. I think the rule should say explicitly that a contradicted GPA is unusable unless an official transcript resolves it. For scoring, the academic score should be reduced and the contradiction should be flagged for committee review.

**5. How close were your top two candidates?** If they were within 0.05, say
what you would tell the committee and what you would change in the extraction
to make that call defensible.

> The top two candidates were story-01 with 4.4 and story-04 with 3.9, a difference of 0.50. They were not within 0.05, so I would tell the committee that the computed result is not a tie in this run. If they had been very close, I would make the extraction more defensible by adding more detailed evidence quotes for experience relevance and publication status.

---

## Reflection (optional, one short paragraph)

> Next time I build reliable structured output, I will separate the model's job from the program's job earlier. The model can extract and score, but code should validate the shape, check deterministic rules, compute totals, and decide what is safe to use downstream.
