## 1. Environment and deployment hardening

- [x] 1.1 Add the checked-in environment template and replace committed sensitive deployment defaults with environment-sourced references
- [x] 1.2 Add the `gosqlbot-app` health contract to Compose and align deployment configuration with the new readiness expectations

## 2. Repository quality gates

- [x] 2.1 Expand local pre-merge hooks or equivalent fast validation entry points so frontend and backend checks are both represented
- [x] 2.2 Update CI quality workflows to enforce the defined stack-appropriate frontend/backend validation matrix

## 3. Documentation and verification

- [x] 3.1 Update README, contributor guidance, and agent-facing path/setup references to match the hardened configuration workflow
- [x] 3.2 Verify the environment bootstrap flow, Compose health behavior, and quality-gate execution paths remain consistent with the OpenSpec contract
