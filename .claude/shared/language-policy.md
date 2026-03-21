# Language Policy

## Core Rule

- Match the language of the latest substantive user input unless the user explicitly requests another language.

## Distinction

- `interaction_language`: language used in assistant replies, status updates, and direct questions to the user.
- `artifact_language`: language used for natural-language sections in generated docs, reports, and summaries.

## Defaults

- Default `interaction_language` to the user's latest substantive input.
- Default `artifact_language` to `interaction_language`.
- If the user explicitly requests another language, follow that request.

## Keep In English

- File names and paths
- JSON or YAML keys
- Schema field names
- CLI commands and shell snippets
- Code identifiers
- Workflow IDs and stage IDs
- Metric keys when they are part of a protocol or schema
- Placeholder tokens such as `{project_name}`
- Any field explicitly marked as English-only

## Template Interpretation

- English wording in templates and examples is structural guidance, not a requirement that the final artifact must be in English.
- Preserve the required section structure, field set, and decision vocabulary.
- Localize headings, table notes, checklist prose, and narrative text to `artifact_language` unless a field is explicitly marked as English-only.
