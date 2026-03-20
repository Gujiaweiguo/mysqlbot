## Context

The repository already writes audit entries through `system_log` decorators and stores sufficient metadata to power the operation log UI. The frontend page `system/audit` is complete and expects three backend contracts: paginated listing, filter option discovery, and Excel export. However, the backend router for audit management is not currently exposed through the main API registration, leaving a gap between recorded data and administrator-facing visibility.

## Goals / Non-Goals

**Goals:**
- Restore first-party APIs that let administrators browse recorded operation logs.
- Support the filter set already used by the frontend: operation type, user, workspace, status, and time range.
- Support exporting the current filtered result set to Excel.
- Preserve the current audit-writing infrastructure and avoid redesigning logging semantics.

**Non-Goals:**
- Redesign which operations are logged.
- Introduce a new log storage engine.
- Rebuild the frontend operation log page.

## Decisions

### 1. Reuse the existing audit log storage and query utilities
The change will build on `common.audit.models.log_model`, `logger_decorator`, and `log_utils` rather than creating a new audit schema.

**Why:** The repository already records the events needed by the page. The missing capability is the read/query/export surface.

### 2. Match the current frontend contract instead of redesigning the page first
The backend will provide the endpoints the page already calls:
- `GET /system/audit/page/{pageNum}/{pageSize}`
- `GET /system/audit/get_options`
- `GET /system/audit/export`

**Why:** The fastest, lowest-risk path is restoring the missing backend contract.

### 3. Keep operation log access admin-focused
The APIs should preserve admin-only access semantics and continue respecting workspace/user dimensions in query results.

**Why:** The page is an administrative surface and should not accidentally widen audit visibility.

## Risks / Trade-offs

- **[Existing audit records may contain resource/module values the page does not fully interpret]** → Keep backend response compatible with current frontend fields and rely on existing translation/display logic.
- **[Exporting very large result sets could be slow]** → Start with the existing all-results export behavior and optimize later only if needed.
- **[Workspace/user option sources may drift from actual log contents]** → Use existing workspace/user APIs for filter options while keeping page filters tolerant of missing historical references.

## Migration Plan

1. Locate or restore the backend audit router and register it in the main API router.
2. Implement/restore paginated query, filter options, and export endpoints to match the frontend contract.
3. Add tests for list retrieval, options retrieval, and export response behavior.
4. Validate the operation log page on the public deployment.

## Open Questions

- Should export be limited by current filters only, or also support full-history export regardless of pagination? The current frontend assumes filter-aware full export.
- Should admin-only access remain global, or should future iterations add finer workspace-scoped restrictions?
