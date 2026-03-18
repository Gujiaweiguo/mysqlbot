## Context

The repository includes a `repo-sync` check that depends on external synchronization infrastructure. In practice, the check can fail because of missing or invalid credentials, unreachable remotes, or mirror-specific issues unrelated to the application change under review. Without an explicit execution policy, reviewers cannot tell whether a red `repo-sync` check represents a real release blocker or just missing external prerequisites.

The design goal is to define `repo-sync` as an intentional operational gate instead of leaving it as an always-on opaque failure mode.

## Goals / Non-Goals

**Goals:**
- Define when `repo-sync` is expected to run and when it is allowed to skip.
- Make prerequisite failures explicit and diagnosable.
- Align blocking behavior with actual release or maintenance needs.
- Document operator ownership for credentials and remote targets.

**Non-Goals:**
- Redesign the entire release pipeline.
- Replace the external sync system with a different tool.
- Solve unrelated infrastructure reliability issues beyond the repo-sync contract.

## Decisions

### Decision 1: Make repo-sync policy event- and branch-aware

`repo-sync` will run only in the contexts where synchronization is actually expected, such as protected branches, release flows, or explicit manual dispatch, rather than acting as a generic PR-time blocker by default.

**Why:**
- Ordinary pull requests should not be blocked by mirror operations that are irrelevant to code review.
- Release-facing or mirror-maintenance flows still need explicit sync validation.

**Alternatives considered:**
- Keep repo-sync required on every PR: rejected because it couples application review to external infrastructure instability.

### Decision 2: Validate prerequisites before attempting sync

The workflow will perform explicit preflight checks for required credentials, remote configuration, and supported execution context before attempting synchronization.

**Why:**
- Fast, readable failure reasons are far more actionable than opaque sync command failures.
- Preflight checks also allow clean skip behavior where sync is intentionally not applicable.

**Alternatives considered:**
- Let the sync command fail naturally: rejected because it hides intent and ownership.

### Decision 3: Keep sync ownership and recovery steps in documentation

The operational owner, credential source, target remotes, and recovery path will be documented alongside the workflow policy.

**Why:**
- Repo-sync is an operational concern with external dependencies; maintainers need a clear runbook.
- Without documentation, workflow edits or secret rotations can silently break the gate again.

**Alternatives considered:**
- Encode policy only in workflow YAML: rejected because operators still need a human-readable runbook.

## Risks / Trade-offs

- **[Sync no longer runs on every PR]** → Restrict blocking sync to contexts where it matters and document why PR scope is intentionally narrower.
- **[Preflight checks can drift from real sync requirements]** → Keep the prerequisite list small, explicit, and validated against actual sync commands.
- **[Operator ownership remains ambiguous]** → Record credential ownership and remote targets in the runbook.

## Migration Plan

1. Inventory the current `repo-sync` workflow behavior, credentials, and target remotes.
2. Define the intended execution matrix by event and branch.
3. Add preflight validation and explicit skip/fail behavior.
4. Update repository documentation and branch protection guidance to match the new policy.
5. Validate one context where sync should run and one where it should skip cleanly.

Rollback can restore the previous always-on behavior, but the preferred path is to keep the explicit policy and correct the execution matrix if it proves too narrow or too broad.

## Open Questions

- Should repo-sync run only on `main`/`master`, or also on release branches?
- Should manual dispatch be the only way to force sync outside protected branches?
- Is a skipped repo-sync check acceptable for PRs, or does the workflow need a non-blocking informational result instead?
