## Why

This repository still carries mirror-maintenance workflows for Gitee and CNB, but the current maintainer intent is that these external repository sync paths are no longer needed. Keeping them in place creates avoidable failures on `main`, adds credential and platform maintenance overhead, and makes repository health look worse for reasons unrelated to product code.

## What Changes

- Retire the GitHub-to-Gitee mirror workflow as a maintained repository path instead of continuing to treat it as an expected post-merge operation.
- Evaluate the manual CNB sync workflow under the same policy and remove it as well if it is no longer an intentionally supported mirror path.
- Update repository-sync documentation and spec language so the repository contract reflects decommissioned or manual-only mirror behavior rather than an active operational gate.
- Clarify how maintainers should interpret historical `repo-sync` failures once the mirror workflows are retired.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-sync-gate`: Change the repository sync contract from an active mirror-maintenance gate to a decommissioned or explicitly non-operational path.

## Impact

- Affected workflow files under `.github/workflows/`, especially `sync2gitee.yml` and potentially `sync_to_cnb.yml`
- Maintainer documentation in `docs/repo-sync-gate.md`
- OpenSpec artifacts for `repository-sync-gate`
- GitHub Actions check behavior on `main` if the automatic mirror workflow is removed or restricted
