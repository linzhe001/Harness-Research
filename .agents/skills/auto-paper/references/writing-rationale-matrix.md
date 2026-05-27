# Writing Rationale Matrix

## Purpose

The matrix explains why a unit should change before any sentence is rewritten.
It is the handoff from layout to patch.

## Row Granularity

A unit can be a title, abstract sentence group, paragraph, figure caption,
table note, limitation sentence, or other smallest useful writing unit.

## Required Columns

- `unit_id`
- `source_location`
- `current_text_role`
- `problem_type`
- `reader_question`
- `target_role`
- `evidence_ids`
- `citation_ids`
- `rewrite_action`
- `latex_constraints`
- `overclaim_risk`
- `done_definition`

## Shallow Rationale Failures

The following are not sufficient by themselves:

- `make clearer`
- `improve flow`
- `add citation`
- `shorten`
- `polish language`

Expand each into a reader question, evidence source, risk, and observable done
definition. A patch without a usable matrix row should be blocked.
