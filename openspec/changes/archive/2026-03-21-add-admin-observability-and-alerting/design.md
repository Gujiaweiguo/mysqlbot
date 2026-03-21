## Context

Recent changes restored a large set of first-party admin and runtime capabilities: login bootstrap, authentication settings, platform integration, operation logs, custom prompts, appearance settings, AI model validation, and permission configuration. These flows are now functional, but operational visibility is still thin. Failures would currently be detected mostly through end-user reports or manual browser checks, which is too slow for high-value admin paths.

## Goals / Non-Goals

**Goals:**
- Define a focused observability surface for the critical admin/runtime APIs restored in recent work.
- Ensure the chosen metrics or structured logs are sufficient to detect regressions in production quickly.
- Define alert conditions and operator guidance for the most business-critical API failures.

**Non-Goals:**
- Redesign application business logic or feature behavior.
- Add observability to every endpoint in the system in one pass.
- Replace existing infrastructure with a completely new monitoring stack.

## Decisions

### 1. Focus on the restored high-risk endpoints first
The change will cover the APIs most likely to cause visible admin failures:
- `/system/authentication/*`
- `/system/platform/*`
- `/system/audit/*`
- `/system/custom_prompt/*`
- `/system/appearance`
- `/system/aimodel/*`
- `/ds_permission/*`

**Why:** These are the endpoints touched by the recent first-party restoration work and the pages most likely to regress.

### 2. Prefer low-friction observability additions that fit the current stack
Use existing logging/request infrastructure where possible, then add targeted counters, timing, or structured error events rather than inventing a new observability subsystem.

**Why:** The goal is actionable production visibility with minimal operational risk.

### 3. Pair every alert with an operator-facing interpretation
Each alert condition should map to a short runbook entry or guidance note explaining likely user impact, primary endpoint(s), and first debug step.

**Why:** Alerts without triage guidance create noise and slow incident response.

## Risks / Trade-offs

- **[Too many noisy alerts]** → Start with a small set of high-signal endpoints and conservative thresholds.
- **[Too little signal to catch regressions]** → Include both error-rate and latency-oriented checks where failures might manifest differently.
- **[Implementation tied too tightly to one monitoring backend]** → Keep the change scoped to observability contracts and instrumentation points, not vendor lock-in.

## Migration Plan

1. Inventory critical admin/runtime endpoints and current logging/visibility points.
2. Add structured instrumentation or request-level signal collection for the selected endpoints.
3. Define alert conditions and runbook guidance.
4. Validate the new signals against known failure scenarios or recent regressions.

## Open Questions

- Which monitoring backend or alert transport should be treated as the source of truth if multiple are available?
- Are some endpoints better monitored by structured error events only, rather than continuous metrics?
