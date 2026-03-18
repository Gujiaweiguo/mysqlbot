## Context

The repository currently runs `crate-ci/typos` as a blocking check, but the scan reports many long-standing spelling errors unrelated to the active pull request. This makes the check red even when a PR does not introduce new spelling regressions, which weakens reviewer trust in CI and trains contributors to ignore the signal.

The desired change is not a repository-wide copyediting effort. The immediate need is to make the gate useful for ongoing development while preserving a path to gradually clean historical debt.

## Goals / Non-Goals

**Goals:**
- Make PR-time spelling failures actionable and attributable to the current change.
- Preserve the ability to catch newly introduced spelling errors.
- Provide an explicit configuration mechanism for approved project-specific vocabulary.
- Keep a documented path for later historical typo cleanup.

**Non-Goals:**
- Fix every historical spelling issue in one change.
- Introduce a new spell-checking toolchain.
- Turn spelling validation into a broad editorial/style review process.

## Decisions

### Decision 1: Scope blocking PR checks to files touched by the pull request

The blocking spelling gate will validate only files changed by the current PR, rather than failing on the entire repository backlog.

**Why:**
- This restores immediate CI signal without requiring a large cleanup campaign.
- It aligns gate ownership with the contributor who can actually fix the issue.

**Alternatives considered:**
- Keep whole-repo blocking scans: rejected because historical debt continues to drown out actionable failures.
- Disable spelling checks entirely: rejected because it removes protection against new typo regressions.

### Decision 2: Manage approved project vocabulary through explicit repository config

Project-specific tokens, acronyms, and intentional identifiers will be recorded in repository-managed spelling config instead of relying on ad hoc failures or repeated manual waivers.

**Why:**
- Domain terms such as product names, acronyms, and API identifiers are expected in this codebase.
- Explicit config makes reviews predictable and avoids repeated false positives.

**Alternatives considered:**
- Inline ignore markers only: rejected because they spread policy across many files.

### Decision 3: Preserve whole-repo visibility as a non-blocking maintenance path

Historical typo debt should remain visible through a non-blocking report, scheduled run, or documented backlog process rather than disappearing completely.

**Why:**
- The team still needs a path to reduce historical debt over time.
- Separating visibility from PR blocking prevents CI noise while keeping the problem measurable.

**Alternatives considered:**
- Ignore the historical backlog permanently: rejected because it converts technical debt into invisible debt.

## Risks / Trade-offs

- **[PR-only scope can miss untouched historical typos]** → Keep a documented maintenance path for periodic whole-repo scans.
- **[Over-broad approved-word list can weaken the gate]** → Require explicit review for new allowlist entries.
- **[Changed-file detection may miss generated or renamed paths]** → Validate file selection logic against representative PR scenarios.

## Migration Plan

1. Inventory current typo failures and classify them into historical debt vs. project-specific vocabulary.
2. Introduce repository spelling config and reviewed allowlist entries.
3. Update CI so PR-time blocking checks run against changed files only.
4. Add documentation describing how to approve new terms and how to run broader cleanup sweeps.
5. Validate the new gate with one PR that contains no new typos and one that intentionally introduces a typo.

Rollback can revert to the previous whole-repo behavior if changed-file scoping proves unreliable, but the expectation is to keep the new scoped gate and improve its file selection logic instead.

## Open Questions

- Should the whole-repo maintenance scan run on a schedule, manual dispatch, or both?
- Should documentation files be included in the first scoped rollout, or should the first version focus on code/config only?
