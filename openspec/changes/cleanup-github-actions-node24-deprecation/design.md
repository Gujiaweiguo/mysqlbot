## Context

Current CI runs pass functionally but emit Node.js 20 deprecation warnings from JavaScript-based GitHub Actions. This warning noise reduces signal quality and creates future breakage risk when runner defaults fully remove Node 20 execution paths.

## Goals / Non-Goals

**Goals:**
- Ensure affected CI workflows execute with Node 24-compatible action runtime behavior.
- Keep the change minimal and limited to workflow configuration.
- Preserve existing regression/quality gate behavior and acceptance criteria.

**Non-Goals:**
- No product/backend/frontend logic changes.
- No restructuring of workflow topology or gate policy.
- No dependency or toolchain upgrades outside workflow runtime compatibility.

## Decisions

- Apply a workflow-level compatibility setting in the targeted CI workflows so JavaScript actions run on Node 24 runtime paths.
  - Rationale: smallest operational change that directly addresses the deprecation warning and future runner compatibility.
  - Alternative considered: upgrading all actions to newer major versions only. Rejected for this change because it introduces broader behavioral drift than needed.

- Validate by rerunning the affected workflows and confirming gate outcomes are unchanged.
  - Rationale: ensures the compatibility setting does not alter product-facing regression results.

## Risks / Trade-offs

- [Risk] Some legacy actions might behave differently when forced to Node 24 runtime. → Mitigation: scope to known workflows, rerun gates immediately, and revert quickly if regressions appear.
- [Trade-off] This change does not modernize action versions by itself. → Mitigation: keep version-upgrade work as separate follow-up maintenance if needed.
