## Why

`repo-sync` currently fails as an opaque external-system check, which makes pull requests look unhealthy even when the application changes themselves are valid. We need an explicit contract for when repository sync is expected to run, what credentials it depends on, and whether it is blocking for ordinary development flows.

## What Changes

- Define the execution policy for `repo-sync`, including supported branches/events and whether it is blocking or optional in each context.
- Document the external dependencies required for repo synchronization, such as credentials, remote targets, and operator ownership.
- Add preflight validation or skip behavior so missing sync prerequisites fail with an explicit reason instead of an opaque red check.
- Align repository settings and workflow behavior with the intended role of `repo-sync` in release and maintenance flows.

## Capabilities

### New Capabilities
- `repository-sync-gate`: Defines when repository synchronization runs, what prerequisites it requires, how failures are classified, and how maintainers operate the sync path safely.

### Modified Capabilities
- None.

## Impact

- Affected areas will likely include repo-sync workflow logic, secrets/credential documentation, branch protection expectations, and maintainer operating docs.
- CI semantics change from an opaque failing external check to an explicit policy-driven sync gate.
- Release and mirror-maintenance responsibilities become clearer for maintainers and reviewers.
