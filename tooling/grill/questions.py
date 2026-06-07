"""Question lenses and round contracts used by Grill draft tooling."""

from __future__ import annotations

import argparse
import json
from typing import Any

EXIT_OPTIONS: dict[str, str] = {
    "continue_grill": "Keep questioning because at least one intent gap is blocking.",
    "grill_draft_ready": "Draft intent is clear enough to hand to prepare or bridge.",
    "bridge_wf1_wf3": "Operator wants canonical WF1-WF3 artifacts and gates.",
    "pivot": "Operator wants to change direction before execution.",
    "abandon": "Operator wants to stop this idea.",
}

MATURITY_GAPS: list[dict[str, str]] = [
    {
        "key": "operator_observation",
        "status": "open",
        "blocking_question": (
            "What concrete observation makes this project worth testing?"
        ),
    },
    {
        "key": "candidate_claim",
        "status": "open",
        "blocking_question": (
            "What is the strongest claim this project is trying to support?"
        ),
    },
    {
        "key": "falsifier",
        "status": "open",
        "blocking_question": "Which result would make the idea not worth continuing?",
    },
    {
        "key": "metric_or_signal",
        "status": "open",
        "blocking_question": (
            "Which metric or evaluation signal distinguishes success from noise?"
        ),
    },
    {
        "key": "baseline_or_negative_control",
        "status": "open",
        "blocking_question": (
            "Which baseline or negative control would a reviewer expect?"
        ),
    },
    {
        "key": "claim_boundary",
        "status": "open",
        "blocking_question": (
            "If the first experiment works, what is the maximum claim allowed?"
        ),
    },
    {
        "key": "pivot_abort_condition",
        "status": "open",
        "blocking_question": "When should the project pivot or stop?",
    },
    {
        "key": "execution_readiness",
        "status": "open",
        "blocking_question": (
            "Which dataset, baseline, command, or budget input blocks prepare?"
        ),
    },
]

QUESTION_LENSES: dict[str, list[dict[str, str]]] = {
    "facilitator": [
        {
            "id": "facilitator_1",
            "question": "What decision should this Grill round resolve?",
            "why_this_matters": (
                "A round without a decision target turns into open-ended "
                "brainstorming."
            ),
            "answer_type": "free_text",
        },
        {
            "id": "facilitator_2",
            "question": "Which current open question blocks the next safe action?",
            "why_this_matters": (
                "Grill should surface the next bottleneck instead of "
                "collecting trivia."
            ),
            "answer_type": "free_text",
        },
        {
            "id": "facilitator_3",
            "question": (
                "Do you want another Grill round, a pivot, abandon, or a "
                "draft handoff?"
            ),
            "why_this_matters": "The operator owns the segment boundary decision.",
            "answer_type": "choice",
        },
    ],
    "intake": [
        {
            "id": "intake_1",
            "question": "What concrete observation motivates this project?",
            "why_this_matters": (
                "The observation anchors the idea in a real failure or "
                "opportunity."
            ),
            "answer_type": "free_text",
        },
        {
            "id": "intake_2",
            "question": "What failure mode or limitation should the project explain?",
            "why_this_matters": (
                "The failure mode defines what the project must make clearer."
            ),
            "answer_type": "free_text",
        },
        {
            "id": "intake_3",
            "question": "Which result would make the project not worth continuing?",
            "why_this_matters": (
                "A falsifier prevents the idea from drifting without a stop "
                "condition."
            ),
            "answer_type": "free_text",
        },
    ],
    "skeptic": [
        {
            "id": "skeptic_1",
            "question": (
                "What is the strongest simpler explanation for the expected "
                "result?"
            ),
            "why_this_matters": (
                "A simpler explanation can invalidate the novelty story."
            ),
            "answer_type": "free_text",
        },
        {
            "id": "skeptic_2",
            "question": "Which baseline could make the idea look unnecessary?",
            "why_this_matters": (
                "Missing this baseline creates the highest reviewer risk."
            ),
            "answer_type": "free_text",
        },
        {
            "id": "skeptic_3",
            "question": (
                "What claim would be overstated even if the first experiment "
                "works?"
            ),
            "why_this_matters": (
                "Claim boundaries keep early positive results from being "
                "oversold."
            ),
            "answer_type": "free_text",
        },
    ],
    "methodologist": [
        {
            "id": "methodologist_1",
            "question": "Which metric or protocol choice could bias the conclusion?",
            "why_this_matters": (
                "A biased metric can make the wrong hypothesis look successful."
            ),
            "answer_type": "free_text",
        },
        {
            "id": "methodologist_2",
            "question": "What dataset or split fact must be verified before execution?",
            "why_this_matters": (
                "Unverified data assumptions should stop prepare before "
                "automation starts."
            ),
            "answer_type": "path",
        },
        {
            "id": "methodologist_3",
            "question": "What negative result would still be informative?",
            "why_this_matters": (
                "A useful negative result keeps iteration decisions grounded."
            ),
            "answer_type": "free_text",
        },
    ],
    "implementation": [
        {
            "id": "implementation_1",
            "question": "Which local path, command, or dependency is still unknown?",
            "why_this_matters": (
                "Unknown execution inputs become typed pending requests in "
                "prepare."
            ),
            "answer_type": "path",
        },
        {
            "id": "implementation_2",
            "question": "What is the smallest runnable slice that tests the core risk?",
            "why_this_matters": (
                "The first build target should prove the highest-risk "
                "assumption."
            ),
            "answer_type": "free_text",
        },
        {
            "id": "implementation_3",
            "question": (
                "Which external download or long-running action needs "
                "approval first?"
            ),
            "why_this_matters": (
                "External downloads and long runs need explicit operator "
                "policy."
            ),
            "answer_type": "approval",
        },
    ],
    "claim_boundary": [
        {
            "id": "claim_boundary_1",
            "question": (
                "If the experiment works, what is the maximum defensible "
                "claim?"
            ),
            "why_this_matters": (
                "The release claim cannot exceed what the experiment can "
                "support."
            ),
            "answer_type": "free_text",
        },
        {
            "id": "claim_boundary_2",
            "question": "Which attractive claim should this project explicitly avoid?",
            "why_this_matters": (
                "Forbidden claims make later paper or release writing safer."
            ),
            "answer_type": "free_text",
        },
        {
            "id": "claim_boundary_3",
            "question": (
                "Which result would force a pivot rather than a smaller "
                "wording change?"
            ),
            "why_this_matters": (
                "Pivot criteria separate research direction changes from "
                "ordinary debugging."
            ),
            "answer_type": "free_text",
        },
    ],
}


def maturity_gap_template() -> list[dict[str, str]]:
    return [dict(item) for item in MATURITY_GAPS]


def question_round(
    lens: str = "intake",
    *,
    answer_summary: str = "",
    risk: str = "",
    max_questions: int = 4,
) -> dict[str, Any]:
    if lens not in QUESTION_LENSES:
        known = ", ".join(sorted(QUESTION_LENSES))
        raise ValueError(f"unknown Grill lens {lens!r}; expected one of {known}")
    if max_questions < 1:
        raise ValueError("max_questions must be positive")
    return {
        "schema_version": 2,
        "lens": lens,
        "input_state": {
            "answer_summary": answer_summary.strip() or "pending",
            "risk": risk.strip() or "pending",
        },
        "questions": [dict(item) for item in QUESTION_LENSES[lens][:max_questions]],
        "gap_check": maturity_gap_template(),
        "exit_options": dict(EXIT_OPTIONS),
    }


def render_markdown(round_payload: dict[str, Any]) -> str:
    lines = [f"## {round_payload['lens']} questions", ""]
    for item in round_payload["questions"]:
        answer_type = item.get("answer_type", "free_text")
        why = item.get("why_this_matters", "Clarifies a blocking Grill gap.")
        lines.append(f"- `{item['id']}` ({answer_type}): {item['question']}")
        lines.append(f"  Why: {why}")
    lines.extend(
        [
            "",
            "## Maturity gap template",
            "",
            "| Gap | Status | Blocking question |",
            "| --- | --- | --- |",
        ]
    )
    for item in round_payload.get("gap_check", []):
        lines.append(
            "| {key} | {status} | {question} |".format(
                key=item.get("key", "unknown"),
                status=item.get("status", "open"),
                question=item.get("blocking_question", "pending"),
            )
        )
    lines.extend(["", "## Exit options", ""])
    for key, summary in round_payload.get("exit_options", {}).items():
        lines.append(f"- `{key}`: {summary}")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print Grill question lenses.")
    parser.add_argument("--lens", default="intake", choices=sorted(QUESTION_LENSES))
    parser.add_argument("--answer-summary", default="")
    parser.add_argument("--risk", default="")
    parser.add_argument("--max-questions", type=int, default=4)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = question_round(
        args.lens,
        answer_summary=args.answer_summary,
        risk=args.risk,
        max_questions=args.max_questions,
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_markdown(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
