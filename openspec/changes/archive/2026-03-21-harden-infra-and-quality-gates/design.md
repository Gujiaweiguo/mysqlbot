## Context

The repository already supports local and containerized development, but several foundational safety contracts remain implicit. `docker-compose.yaml` still carries hardcoded sensitive defaults, the application container does not publish a Compose-level health contract, and repository validation is stronger for Python than for the frontend stack. Those gaps increase operator risk and make merge safety depend too much on tribal knowledge.

This change is intentionally a hardening pass, not a product feature change. The goal is to make the existing topology and contribution workflow safer and more repeatable before larger refactors land on top of them.

## Goals / Non-Goals

**Goals:**
- Remove active secret values and unsafe defaults from checked-in deployment configuration.
- Introduce a checked-in environment template that makes local/container bootstrap explicit.
- Define a Compose-visible health contract for the application service.
- Establish symmetric frontend/backend quality gates across local hooks and CI.
- Align core contributor/operator documentation with the hardened workflow.

**Non-Goals:**
- Splitting the runtime into additional services or redesigning deployment topology.
- Adding new product behavior, API endpoints, or user-facing features.
- Introducing heavyweight policy tooling beyond the repository's current lint/type/build/test stack.

## Decisions

### Decision 1: Separate checked-in templates from live secret material

The repository will provide a checked-in `.env.example` that contains placeholders or clearly non-sensitive bootstrap defaults, while real sensitive values stay environment-sourced through `.env` or deployment environment variables.

**Why:**
- Hardcoded live-looking values in committed deployment files make onboarding easier in the short term but create long-lived security and operational risk.
- A template preserves discoverability without encouraging operators to reuse insecure defaults.

**Alternatives considered:**
- Keep current defaults in Compose for convenience: rejected because it normalizes unsafe deployments.

### Decision 2: Define application readiness at the Compose contract layer

The application service will publish an explicit health contract that operators and Compose can inspect independently from PostgreSQL readiness.

**Why:**
- Today the deployment contract proves database readiness but not application readiness.
- A visible app health signal improves startup troubleshooting and future automation.

**Alternatives considered:**
- Rely only on process startup and logs: rejected because it remains too implicit for automation and support.

### Decision 3: Use a symmetric quality-gate matrix across stacks

Backend and frontend validation will be treated as first-class merge gates, with fast local hooks for common checks and CI enforcing the full stack-appropriate validation matrix.

**Why:**
- Current validation favors Python tooling, while frontend formatting/lint/type/build checks are easier to miss until later.
- Symmetry is more important than maximizing strictness in one pass.

**Alternatives considered:**
- Put all checks only in CI: rejected because the feedback loop stays slower than necessary.

### Decision 4: Keep documentation changes close to the contract changes

README/operator instructions, contributor workflow guidance, and agent-facing path references will be updated in the same hardening change rather than as a follow-up.

**Why:**
- Configuration hardening without documentation alignment quickly drifts.
- These updates are low-risk and tightly coupled to the behavior change.

**Alternatives considered:**
- Defer docs to a later polish pass: rejected because the new contract would be underspecified during rollout.

## Risks / Trade-offs

- **[Local setup friction increases]** → Provide a complete `.env.example` with clear placeholders and documented copy steps.
- **[Healthcheck becomes flaky]** → Reuse a lightweight health signal that matches actual application readiness, not a brittle deep dependency probe.
- **[More local hooks slow commits]** → Keep pre-commit focused on fast checks and leave heavier validation for CI.
- **[Docs drift from scripts/config]** → Update docs and machine-checked gates in the same implementation sequence.

## Migration Plan

1. Add the proposal, design, and spec contracts for environment templates, quality gates, and deployment hardening.
2. Introduce `.env.example` and replace hardcoded sensitive values in checked-in deployment config with environment-driven references.
3. Add application health signaling to Compose and align deployment docs with the new setup flow.
4. Expand pre-commit and CI workflows so frontend and backend checks are both represented.
5. Verify documented bootstrap flow, Compose config rendering, and stack-appropriate quality checks.

Rollback is straightforward: restore the previous config/docs and remove the new gate wiring if the first hardening pass proves too disruptive.

## Open Questions

- None for this pass.
