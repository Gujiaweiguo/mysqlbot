## 1. Custom prompt management

- [x] 1.1 Map the existing `CustomPrompt` model and internal CRUD helper to the current frontend management page contract.
- [x] 1.2 Implement backend list/read APIs for custom prompts by prompt type.
- [x] 1.3 Implement backend create/update and delete APIs for custom prompts.
- [x] 1.4 Implement backend export behavior for custom prompts by prompt type.

## 2. Appearance settings management

- [x] 2.1 Map the current appearance page fields to the persisted parameter keys and image references already used by the system.
- [x] 2.2 Implement or complete backend save/update behavior for appearance settings so the page can persist login and top-bar configuration.
- [x] 2.3 Implement or complete image replacement behavior for appearance assets using the first-party file utility layer.

## 3. Validation and regression coverage

- [x] 3.1 Add backend tests for custom prompt list/read/write/delete/export behavior.
- [x] 3.2 Add backend tests for appearance settings load/save behavior and image replacement flows.
- [x] 3.3 Run frontend build and public browser checks for `/#/set/prompt` and `/#/system/setting/appearance` to confirm the pages load and save against first-party backend APIs.
