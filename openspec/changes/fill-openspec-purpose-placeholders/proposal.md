## Why

Many main OpenSpec capability specs still carry the archive-time placeholder `TBD - created by archiving change ...` in their `Purpose` section. That leaves the canonical specs harder to scan, weakens spec readability, and forces readers to jump into archived changes to understand what each capability is for.

## What Changes

- Define a documentation-hygiene contract for canonical OpenSpec capability specs so their `Purpose` sections are explicit and no longer rely on archive placeholders.
- Replace remaining placeholder `Purpose` text in affected main specs under `openspec/specs/**` with concise capability summaries grounded in their archived source changes and current requirement bodies.
- Keep this cleanup limited to spec metadata clarity; do not change requirement meaning, scenarios, or product behavior.

## Capabilities

### New Capabilities

- `main-spec-purpose-hygiene`: Canonical OpenSpec capability specs carry explicit purpose text instead of archive-time placeholder text.

### Modified Capabilities

None.

## Impact

- Affected files are main spec documents under `openspec/specs/**/spec.md`
- Source context comes from archived change proposals under `openspec/changes/archive/**`
- No application code, API behavior, or runtime system changes are expected
