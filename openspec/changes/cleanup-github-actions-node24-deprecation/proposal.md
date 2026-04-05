## Why

Recent GitHub Actions runs emit Node.js 20 deprecation warnings for core workflow actions. We should remove this CI runtime risk now so regression and quality signals stay focused on product behavior instead of platform deprecation noise.

## What Changes

- Add a small CI compatibility update in workflow configuration so Actions jobs run with Node.js 24-compatible behavior.
- Keep the change scoped to workflow runtime compatibility only; do not alter product logic or regression assertions.
- Validate that affected workflows still run successfully after the compatibility update.

## Capabilities

### New Capabilities
- _None_

### Modified Capabilities
- `repository-quality-gates`: CI workflow quality gates also require a supported GitHub Actions JavaScript runtime configuration to avoid deprecated Node 20 execution paths.

## Impact

- Affected code: `.github/workflows/*.yml`
- APIs/dependencies: no product API changes, no runtime dependency additions
- Systems: GitHub Actions execution environment for existing quality/regression workflows
