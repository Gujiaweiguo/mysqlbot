## 1. Restore operation log query APIs

- [x] 1.1 Identify the existing backend audit router/query implementation and map it to the frontend `audit.ts` contract.
- [x] 1.2 Register the audit router in `backend/apps/api.py` so the operation log endpoints are actually exposed.
- [x] 1.3 Restore or implement `GET /system/audit/page/{pageNum}/{pageSize}` to return the paginated result shape used by the frontend page.
- [x] 1.4 Restore or implement `GET /system/audit/get_options` to return the operation-type filter tree used by the frontend page.
- [x] 1.5 Restore or implement `GET /system/audit/export` to return an Excel export of the filtered result set.

## 2. Validate filtering and admin access

- [x] 2.1 Ensure the restored audit APIs support filtering by operation type, user, workspace, status, and time range as requested by the frontend query format.
- [x] 2.2 Verify that operation log APIs remain restricted to authorized administrative users.

## 3. Regression coverage

- [x] 3.1 Add backend tests for operation log list retrieval and filter option retrieval.
- [x] 3.2 Add backend tests for operation log export behavior.
- [x] 3.3 Run public-page/browser verification for `/#/system/audit` and confirm the page loads, filters initialize, and export no longer fails due to missing endpoints.
