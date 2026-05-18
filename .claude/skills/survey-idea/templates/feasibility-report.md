# Feasibility Report Template

## context_summary Standard Format

Every output file must begin with a context_summary block, no more than 20 lines:

```markdown
<context_summary>
- **Project:** {project_name}
- **Current Stage:** WF1 - Idea Research
- **Prior Inputs:** User Idea description
- **Deliverables:** Feasibility_Report.md
- **Key Conclusions:**
  1. {conclusion_1}
  2. {conclusion_2}
- **Open Issues:** {open_issues}
- **Next Step:** WF2 idea-debate
</context_summary>
```

## Full Template

```markdown
# Feasibility Report: {project_name}

<context_summary>
- **Idea Overview:** [one-sentence description]
- **Search Time Range:** {start_date} to {end_date}
- **Search Keywords:** {keywords}
- **Related Paper Count:** {paper_count}
- **Most Relevant Competitor:** {top_competitor}
- **Intent Summary:** {one_sentence_user_goal}
</context_summary>

## Evidence Sources

| Source | Why It Was Read | Key Facts Used |
|--------|-----------------|----------------|
| {path_or_url_or_query} | | |

## Explore Intake Grill

Record the user's own intent before broad research begins.

| Category | Answer | Survey / Contract / Build Impact |
|----------|--------|-----------------------------------|
| User goal | | |
| Original motivation | | |
| Target task / data / user | | |
| Success shape | | |
| Non-goals | | |
| Resource constraints | | |
| Personal preferences | | |
| Known concerns | | |

## Explore Synthesis Grill

Use collected Conclusion Evidence to ask only questions that affect Contract or
Build boundaries.

| Question | Triggering Source Artifact | Affects Artifact | Current Answer or Open Issue |
|----------|----------------------------|------------------|------------------------------|
| | | Evaluation Contract / Baseline Contract / Claim Boundary / first slice / pivot condition | |

## Verified Facts

- ...

## Inferences

- ...

## Open Questions

- ...

## 1. Feasibility Score

**Overall Score: {total_score}/10**

| Dimension | Score | Weight | Weighted | Notes |
|-----------|-------|--------|----------|-------|
| Novelty | /10 | 0.30 | | |
| Technical Feasibility | /10 | 0.25 | | |
| Impact | /10 | 0.25 | | |
| Implementation Difficulty | /10 | 0.10 | | |
| Resource Requirements | /10 | 0.10 | | |

## 2. Gap Matrix

| Dimension | Current SOTA | This Idea's Improvement | Estimated Gain | Confidence |
|-----------|-------------|------------------------|----------------|------------|
| Accuracy | | | | |
| Speed | | | | |
| Robustness | | | | |
| Generalization | | | | |

## 3. Top 5 Competitor Analysis

### 3.1 {competitor_name}
- **Paper:** {title}, {venue} {year}
- **Core Method:** ...
- **Difference from This Idea:** ...
- **Known Limitations:** ...

## 4. Prerequisite Checklist

- [ ] Baselines to reproduce: ...
- [ ] Datasets to prepare: ...
- [ ] Papers to read: ...
- [ ] Techniques to master: ...

## 5. Risk Assessment

| Risk Item | Probability | Impact | Mitigation |
|-----------|------------|--------|------------|

## 6. Recommendation

**Decision: PROCEED / PIVOT / ABANDON**

**Rationale:** ...

**Next Steps:** ...
```
