## Why

The repository now boots and runs without `sqlbot-xpack`, but several admin capabilities still stop at placeholder or partial implementations. Authentication settings, platform integration, and third-party user provisioning all expose frontend pages while lacking the backend contracts and runtime flows required by the documented X-Pack behavior, which leaves the product in an inconsistent state for administrators.

## What Changes

- Implement first-party management APIs and persistence flows for authentication settings covering LDAP, OIDC, CAS, OAuth2, and related enable/disable and validation actions.
- Implement first-party platform integration management for WeCom, DingTalk, and Lark, including configuration storage, validation/test connection, and login-related integration metadata.
- Implement third-party platform user provisioning settings so external-login users can be auto-created with controlled default workspace and role assignment.
- Wire the login page and related admin pages to these first-party capabilities so configured providers affect visible login options and runtime behavior.
- Add targeted validation and regression coverage for admin configuration flows and login/platform interactions.

## Capabilities

### New Capabilities
- `authentication-settings-management`: Manage authentication providers such as LDAP, OIDC, CAS, and OAuth2, including configuration, validation, and enablement state.
- `platform-integration-management`: Manage enterprise platform integrations such as WeCom, DingTalk, and Lark, including configuration, validation, and login/sync-related integration settings.
- `third-party-user-provisioning-settings`: Configure how third-party authenticated users are automatically created, assigned to workspaces, and given default roles.

### Modified Capabilities
<!-- None. This change adds first-party admin capabilities that are currently missing or incomplete. -->

## Impact

- Affected frontend pages: `frontend/src/views/system/authentication/*`, `frontend/src/views/system/platform/*`, `frontend/src/views/system/parameter/xpack/PlatformParam.vue`, and login-related views/components.
- Affected frontend APIs: `frontend/src/api/auth.ts`, `frontend/src/api/setting.ts`, login/bootstrap request flows, and platform-related pages.
- Affected backend systems: `backend/apps/system/api/*`, `backend/apps/system/models/system_model.py`, user/platform linking models, authentication storage and validation flows, and login integration paths.
- Operational impact: restores documented admin capabilities for authentication and platform integration without reintroducing the removed `sqlbot-xpack` dependency.
