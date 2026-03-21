## Why

The repository's deployment and merge-safety contracts still have a few sharp edges: Compose configuration carries hardcoded sensitive defaults, the application service lacks an explicit health contract at the Compose layer, and frontend/backend quality enforcement is not yet symmetrical across local hooks and CI. We need to harden those foundations now so routine delivery becomes safer without changing product behavior.

## What Changes

- Move sensitive deployment defaults and local bootstrap values behind environment-driven configuration, with a checked-in template for operator and developer setup.
- Extend the containerized deployment contract so the application service exposes an explicit health/readiness signal instead of relying only on dependent service checks.
- Define repository quality gates that cover both backend and frontend stacks in pre-commit and CI workflows.
- Align operator/developer documentation with the supported environment and validation workflow introduced by the hardening pass.

## Capabilities

### New Capabilities
- `environment-configuration-template`: Defines the checked-in environment template and placeholder-only rules for local and containerized setup.
- `repository-quality-gates`: Defines the required frontend/backend validation gates that protect merges and local pre-merge checks.

### Modified Capabilities
- `containerized-deployment`: Extend the deployment contract with application health signaling and environment-sourced sensitive configuration.

## Impact

- Affected files will likely include `docker-compose.yaml`, `README.md`, `.env.example`, `.pre-commit-config.yaml`, `.github/workflows/quality-check.yml`, and related contributor/operator docs.
- Runtime topology remains `gosqlbot-app` plus backing services, but startup and operator configuration become more explicit and safer.
- No product-facing feature behavior should change; the main impact is stronger deployment hygiene and more reliable engineering gates.
