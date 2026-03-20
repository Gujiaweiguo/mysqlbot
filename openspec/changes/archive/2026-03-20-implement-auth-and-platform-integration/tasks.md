## 1. Authentication settings management

- [x] 1.1 Inventory the existing `sys_authentication` records and define the backend response contract needed by `frontend/src/views/system/authentication/index.vue`.
- [x] 1.2 Implement backend list/read APIs for authentication providers so the admin page can load persisted LDAP, OIDC, CAS, and OAuth2 records.
- [x] 1.3 Implement backend update/create APIs for authentication provider configuration and enable/disable actions.
- [x] 1.4 Implement provider validation/test-connection behavior and wire the result back to the admin page contract.
- [x] 1.5 Replace the placeholder login bootstrap status route with provider status derived from persisted configuration.

## 2. Platform integration management

- [x] 2.1 Inventory the frontend platform integration contract and map WeCom, DingTalk, and Lark settings to first-party backend models/services.
- [x] 2.2 Implement backend list/read APIs for enterprise platform integration cards consumed by `frontend/src/views/system/platform/index.vue`.
- [x] 2.3 Implement backend create/update/enable flows for platform integration configuration.
- [x] 2.4 Implement validation/test-connection behavior for platform integration records and return the status shape the frontend expects.
- [x] 2.5 Restore runtime exposure of enabled platform integrations for login or synchronization flows.

## 3. Third-party user provisioning settings

- [x] 3.1 Identify where third-party auto-user defaults should be persisted and add first-party storage or parameter handling for auto-create, default workspace, and default role.
- [x] 3.2 Implement backend read/write APIs for the third-party platform settings consumed by `PlatformParam.vue`.
- [x] 3.3 Integrate provisioning defaults into external-user creation flows so new third-party users receive the configured workspace and role.

## 4. Validation and regression coverage

- [x] 4.1 Add backend tests for authentication provider CRUD, validation, and enable/disable flows.
- [x] 4.2 Add backend tests for platform integration configuration and validation flows.
- [x] 4.3 Add backend tests for third-party user provisioning defaults and workspace/role assignment behavior.
- [x] 4.4 Run frontend build and targeted browser checks covering authentication settings, platform integration, third-party settings, and login page behavior.
