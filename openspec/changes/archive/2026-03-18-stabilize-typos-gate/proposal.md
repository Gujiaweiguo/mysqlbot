## Why

`Spell Check with Typos` is currently a stable source of noisy red CI because the repository already contains a large backlog of historical spelling issues. We need the spelling gate to become actionable for new pull requests now, without requiring a risky repository-wide cleanup first.

## What Changes

- Define a dedicated spelling-quality gate contract for pull requests, including what files are checked and what kinds of failures are blocking.
- Introduce explicit project-level spelling configuration for approved terms, ignored patterns, and historical debt handling.
- Separate "new typo introduced by this PR" from "historical repository typo backlog" so CI signal becomes actionable.
- Document ownership and maintenance rules for the spelling gate so future workflow or dictionary changes do not silently weaken it.

## Capabilities

### New Capabilities
- `spelling-quality-gate`: Defines how CI validates spelling for pull requests, how project-specific words are managed, and how historical typo debt is contained without masking newly introduced errors.

### Modified Capabilities
- None.

## Impact

- Affected areas will likely include typo-check workflow configuration, repository spelling config such as `typos.toml`, and contributor documentation.
- CI semantics change from an all-or-nothing noisy failure mode to a scoped gate that preserves signal for new changes.
- Maintainers gain an explicit process for approving domain-specific terms and managing historical typo debt.
