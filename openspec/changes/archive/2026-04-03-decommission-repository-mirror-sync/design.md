## Context

This repository currently contains two external mirror workflows: automatic GitHub-to-Gitee synchronization on pushes to `main`/`master`, and a manual CNB synchronization workflow. Maintainer intent has changed: these external mirror destinations are no longer part of the repository's desired operating model, so continuing to ship workflows, docs, and specs for them creates avoidable failures and maintenance overhead.

The current `repository-sync-gate` spec and `docs/repo-sync-gate.md` describe repo-sync as an operational path with explicit prerequisites and recovery guidance. That contract now needs to be changed so the documented behavior matches the intended retired state.

## Goals / Non-Goals

**Goals:**
- Remove inactive external mirror workflows from the repository's default maintenance path.
- Ensure the repository spec and docs describe repository sync as retired or non-operational by default.
- Eliminate routine `main` failures caused only by missing external mirror credentials for workflows the project no longer intends to use.

**Non-Goals:**
- Replacing Gitee or CNB sync with another mirror provider.
- Building a new release-distribution process.
- Preserving backward compatibility for external mirror automation that is no longer intentionally supported.

## Decisions

### Decision 1: Decommission automatic GitHub-to-Gitee sync

The `sync2gitee.yml` workflow will no longer be treated as an active repository-maintenance path. The repository should stop triggering GitHub-to-Gitee sync as part of normal pushes to `main`/`master`.

**Why:** The workflow adds red CI unrelated to product code and depends on credentials and platform access that maintainers no longer want to manage.

**Alternative considered:** Keep it as manual-only. This was rejected as the default plan because the user explicitly stated the mirror path is not needed.

### Decision 2: Decommission the manual CNB sync path in the same change

The `sync_to_cnb.yml` workflow should be retired together with the Gitee workflow unless a maintainer explicitly decides the CNB mirror remains a required operational path.

**Why:** Keeping an unused manual sync path still preserves secret dependencies, platform-specific maintenance burden, and policy ambiguity.

**Alternative considered:** Leave CNB untouched because it is manual-only. This was rejected because the repository intent is to stop maintaining external mirror workflows, not merely to stop auto-triggering one of them.

### Decision 3: Update the repository-sync specification instead of deleting history

The existing `repository-sync-gate` capability should be modified to describe retirement/non-operation, rather than erasing the capability history entirely.

**Why:** The repository already has a documented and archived policy for repo-sync. A modified spec preserves the fact that the workflow existed, explains that it is no longer active, and gives maintainers a clear reintroduction boundary if sync is ever needed again.

**Alternative considered:** Delete the spec and docs outright. This was rejected because it loses useful operational history and makes older failures harder to interpret.

## Risks / Trade-offs

- **[Risk] Historical maintainers still expect mirror updates** → **Mitigation:** Update docs to state clearly that external mirrors are retired and must not be assumed current.
- **[Risk] Someone still relies on CNB or Gitee as an unofficial downstream** → **Mitigation:** Call out the retirement in proposal/spec/docs so any remaining dependency is surfaced before implementation lands.
- **[Risk] Branch protection or external automation still references old checks** → **Mitigation:** Include review of required checks and workflow references in implementation tasks.

## Migration Plan

1. Update OpenSpec artifacts to record the decommissioning decision.
2. Remove or disable the external mirror workflow definitions.
3. Update maintainer docs to say repository mirrors are no longer maintained by default.
4. Verify no required check or automation still assumes the retired workflows exist.
5. If an external mirror is needed again later, reintroduce it through a new explicit change.

## Open Questions

- Are any repository settings or branch protection rules still explicitly bound to the `repo-sync` check name?
- Does any downstream release or distribution process still expect the CNB repository to stay current?
