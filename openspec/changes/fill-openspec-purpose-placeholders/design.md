## Context

The repository has accumulated many canonical OpenSpec specs whose `Purpose` sections were never updated after archive. The requirement bodies are already correct, but the top-level summaries are placeholders, which makes the main spec set less readable and forces maintainers to inspect historical change artifacts to understand capability intent.

This cleanup spans many existing spec files but is documentation-only. The important constraint is that the cleanup must not drift from the actual requirement bodies or archived change intent.

## Goals / Non-Goals

**Goals:**
- Replace remaining archive placeholder `Purpose` text in main specs with concise, accurate summaries.
- Derive each summary from the archived source change and the current capability requirements.
- Keep the cleanup mechanical and low-risk by changing only `Purpose` text where placeholders remain.

**Non-Goals:**
- Changing requirement semantics or scenarios.
- Refactoring spec structure beyond the `Purpose` field.
- Cleaning unrelated wording issues in already-complete specs.

## Decisions

### Decision 1: Limit edits to specs that still have the archive placeholder

Only specs with the exact placeholder pattern are updated.

**Why:** This keeps the change bounded and avoids unnecessary churn in already-curated specs.

### Decision 2: Use archived proposals as the primary intent source

Purpose text will be derived first from the archived source change proposal, then checked against the current main spec requirements for accuracy.

**Why:** The proposal explains the original capability intent in concise language, while the current main spec confirms the resulting contract.

### Decision 3: Introduce a lightweight hygiene capability for future reference

This cleanup change records a small documentation-hygiene capability so the repository has an explicit contract that canonical specs should not retain archive placeholders.

**Why:** Without a recorded contract, the same cleanup gap can recur during future archiving work.

## Risks / Trade-offs

- **[Risk] Purpose text overstates capability scope** → **Mitigation:** Keep each summary to one sentence and cross-check it against the existing requirements.
- **[Risk] Large batch editing increases review burden** → **Mitigation:** Limit edits strictly to placeholder `Purpose` lines and verify with grep afterward.
- **[Risk] A proposal summary may not fully match the final archived spec** → **Mitigation:** Use the current main spec as the final correctness check before writing the replacement purpose.

## Migration Plan

1. Identify every main spec with the placeholder `Purpose` text.
2. Map each one to its archived source change.
3. Replace placeholder text with concise, requirement-aligned purpose summaries.
4. Verify no placeholder `Purpose` strings remain in `openspec/specs/**`.

## Open Questions

- None for implementation; the remaining work is mechanical once each archived source mapping is confirmed.
