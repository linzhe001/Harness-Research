"""Question lenses used by Grill draft tooling."""

from __future__ import annotations

import argparse
import json
from typing import Any

QUESTION_LENSES: dict[str, list[str]] = {
    "intake": [
        "What concrete observation motivates this project?",
        "What failure mode or limitation should the project explain?",
        "Which result would make the project not worth continuing?",
    ],
    "skeptic": [
        "What is the strongest simpler explanation for the expected result?",
        "Which baseline could make the idea look unnecessary?",
        "What claim would be overstated even if the first experiment works?",
    ],
    "methodologist": [
        "Which metric or protocol choice could bias the conclusion?",
        "What dataset or split fact must be verified before execution?",
        "What negative result would still be informative?",
    ],
    "implementation": [
        "Which local path, command, or dependency is still unknown?",
        "What is the smallest runnable slice that tests the core risk?",
        "Which external download or long-running action needs approval first?",
    ],
}


def question_round(lens: str = "intake") -> dict[str, Any]:
    if lens not in QUESTION_LENSES:
        known = ", ".join(sorted(QUESTION_LENSES))
        raise ValueError(f"unknown Grill lens {lens!r}; expected one of {known}")
    return {
        "schema_version": 1,
        "lens": lens,
        "questions": [
            {"id": f"{lens}_{index}", "question": question}
            for index, question in enumerate(QUESTION_LENSES[lens], start=1)
        ],
    }


def render_markdown(round_payload: dict[str, Any]) -> str:
    lines = [f"## {round_payload['lens']} questions", ""]
    for item in round_payload["questions"]:
        lines.append(f"- `{item['id']}`: {item['question']}")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print Grill question lenses.")
    parser.add_argument("--lens", default="intake", choices=sorted(QUESTION_LENSES))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = question_round(args.lens)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_markdown(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
