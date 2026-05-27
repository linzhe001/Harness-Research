# Citation Support Bank

## Claim Segmentation

Segment manuscript claims before searching for citations. A citation supports a
claim only if the cited work actually backs that claim, not merely a related
topic.

## Support Grades

- `strong`: directly supports the claim as written.
- `partial`: supports part of the claim; scope must be narrowed.
- `background`: useful context, not direct support.
- `limiting`: documents a limitation, caveat, or counterpoint.
- `metadata_only`: bibliographic metadata only; not claim support.
- `unsupported`: no usable support found.

## Bank Schema

Use these columns in `citation_support_bank.md`:

- `claim_id`
- `claim_text`
- `claim_type`
- `support_grade`
- `source_key`
- `source_type`
- `evidence_sentence`
- `venue_year`
- `recency_bucket`
- `risk_note`
- `allowed_use`
- `needs_user_confirmation`

## Verification

DOI, title, venue, and year checks improve metadata quality. They do not prove
claim support. Claim support must be assessed against the claim text.
