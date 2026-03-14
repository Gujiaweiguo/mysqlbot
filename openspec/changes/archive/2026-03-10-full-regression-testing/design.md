## Context

mysqlbot currently validates behavior in an ad-hoc way across backend, frontend, docker runtime, datasource metadata, and LLM provider integrations. Recent incidents (login page blocked by xpack status fallback, schema visibility confusion, and upstream 429 limits) show that correctness depends on multiple modules and runtime conditions, not a single component-level check. A formal full-regression design is needed so every release can be evaluated with the same deterministic process and evidence standard.

## Goals / Non-Goals

**Goals:**
- Define a repeatable full-regression workflow with explicit quality gates.
- Make intelligent-query tests deterministic by requiring a known fixture schema (`demo_sales`).
- Validate failure-path behavior (especially LLM rate limits and transient errors), not only happy paths.
- Produce release-grade test reports with traceable evidence and gate decisions.

**Non-Goals:**
- Re-architecting application modules, prompt strategy, or provider integration internals.
- Replacing existing lint/build tools.
- Defining long-term performance benchmarking infrastructure.

## Decisions

1. **Gate-based testing contract instead of one-shot checks**
   - Decision: Split regression into mandatory gates (runtime health, backend quality, frontend quality, key user journeys, failure handling, reporting).
   - Why: Prevents “all green except one hidden path” outcomes and makes release decisions auditable.
   - Alternative considered: Single checklist without gates. Rejected because it does not enforce stop/go boundaries.

2. **Fixture-first intelligent-query validation**
   - Decision: Require demo fixture validation (`demo_sales`) before NL2SQL/chat tests.
   - Why: Removes false negatives caused by unstable schemas and missing metadata sync.
   - Alternative considered: Test against arbitrary workspace datasources. Rejected due to non-determinism.

3. **Failure-path parity with happy-path testing**
   - Decision: Treat LLM rate-limit and transient errors as first-class regression checks with expected user-visible outcomes.
   - Why: Real production failures are often upstream; regression must ensure graceful degradation.
   - Alternative considered: Observe failure logs passively. Rejected due to poor reproducibility.

4. **Evidence-backed report as release artifact**
   - Decision: Define a structured report template (scope, env, commands, results, evidence links, unresolved risk, decision).
   - Why: Supports handoff, rollback decisions, and postmortem traceability.
   - Alternative considered: Free-form chat summary. Rejected because it is hard to audit and compare over time.

## Risks / Trade-offs

- **[Risk] Gate execution time increases release cycle latency** → Mitigation: allow parallel execution for independent gates and cache-heavy setup.
- **[Risk] Fixture drift from product assumptions** → Mitigation: include fixture validation and metadata sync checks as an early gate.
- **[Risk] Upstream LLM variability causes flaky results** → Mitigation: define acceptance based on bounded retries + graceful error behavior rather than fixed text output.
- **[Risk] Teams bypass reporting when under deadline pressure** → Mitigation: make report completion a release-exit criterion.

## Migration Plan

1. Introduce the full-regression specification and task sequence.
2. Run one baseline dry-run on current main branch to calibrate expected outputs.
3. Adopt as required pre-release workflow for upcoming iterations.
4. Rollback strategy: if rollout blocks delivery, temporarily run previous process in parallel while keeping spec/report artifacts generated for comparison.

## Open Questions

- Should 429 validation use a controlled mock path in addition to live provider behavior?
- What is the minimum acceptable pass rate for flaky upstream-dependent checks?
- Should regression reports be stored in-repo, artifact storage, or both?
