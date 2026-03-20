## Why

The operation log page already exists in the frontend and the backend already records audit events through decorators and log models, but the public query/export APIs are not wired into the application router. As a result, administrators can trigger the page but cannot actually browse, filter, or export operation logs.

## What Changes

- Restore first-party backend APIs for operation log listing, filter options, and Excel export.
- Expose workspace, user, operation-type, status, and time-range filtering in a way that matches the existing frontend page contract.
- Reconnect the audit query APIs to the current audit log storage so the operation log page can read already-recorded events.
- Add targeted regression coverage for operation log querying and export behavior.

## Capabilities

### New Capabilities
- `operation-log-management`: View, filter, and export recorded audit/operation logs from the admin console.

### Modified Capabilities
<!-- None. This change introduces the missing first-party admin capability surface for operation log browsing/export. -->

## Impact

- Affected frontend page: `frontend/src/views/system/audit/index.vue`
- Affected frontend API wrapper: `frontend/src/api/audit.ts`
- Affected backend systems: audit log query/export routers, `common.audit.models.log_model`, `common.audit.schemas.log_utils`, and route registration in `backend/apps/api.py`
- Operational impact: restores admin visibility into existing logged operations without changing the underlying event-writing decorators.
