## Why

The repository now has first-party runtime support for login, platform integration, embedded management, permissions, and operation logs, but two admin system-configuration areas still stop short of full first-party completion: custom prompts and appearance settings. Both pages already exist in the frontend, but their backend contracts are either incomplete or only partially restored, which leaves administrators with pages that render but cannot reliably complete the full documented management workflow.

## What Changes

- Complete first-party backend management APIs for custom prompts so the existing admin page can list, read, create/update, delete, and export prompt records by type.
- Complete first-party backend save/upload flows for appearance settings so login-page and top-bar settings can be persisted, restored, and previewed consistently.
- Preserve the current frontend UX where possible by making backend contracts align with the pages already present in `system/prompt` and `system/appearance`.
- Add targeted regression coverage for prompt management and appearance settings save/load behavior.

## Capabilities

### New Capabilities
- `custom-prompt-management`: Manage custom prompt records, including list, read, save, delete, and export behavior for SQL, analysis, and prediction prompt types.
- `appearance-settings-management`: Manage appearance settings for the login page and platform top bar, including persisted settings and image upload/replace behavior.

### Modified Capabilities
<!-- None. This change introduces missing first-party admin capability surfaces for existing pages. -->

## Impact

- Affected frontend pages: `frontend/src/views/system/prompt/index.vue`, `frontend/src/views/system/appearance/index.vue`
- Affected frontend APIs: `frontend/src/api/prompt.ts`, appearance-related request flows in the existing settings page
- Affected backend systems: `backend/apps/chat/models/custom_prompt_model.py`, `backend/apps/chat/crud/custom_prompt.py`, system parameter and file utility flows, and new backend routers to expose prompt and appearance management
- Operational impact: completes the remaining system-configuration pages without reintroducing `sqlbot-xpack`
