## 1. Backend contract and validation

- [x] 1.1 Identify the assistant configuration backend contract used by both basic applications and advanced applications, and extend it to accept persisted multi-select workspace IDs and datasource IDs.
- [x] 1.2 Implement backend validation that rejects disabled, missing, or out-of-scope workspaces and datasources during assistant create/update operations.
- [x] 1.3 Update assistant load/edit responses so previously saved workspace and datasource selections are returned in a form-ready shape.

## 2. Resource lookup and runtime scope

- [x] 2.1 Update workspace-scoped datasource lookup behavior so datasource candidates are filtered by the currently selected workspace set.
- [x] 2.2 Update assistant runtime scope resolution to honor persisted workspace and datasource bindings consistently.

## 3. Frontend assistant configuration flows

- [x] 3.1 Update the basic application assistant configuration form to support multi-select workspace and datasource fields, including edit-state hydration.
- [x] 3.2 Update the advanced application assistant configuration form to support the same multi-select workspace and datasource behavior.
- [x] 3.3 Implement the workspace-to-datasource dependency behavior in the UI so datasource options track the selected workspaces and invalid stale choices are cleared or blocked before submit.

## 4. Verification

- [x] 4.1 Add or update backend tests for multi-select persistence, invalid-scope rejection, and assistant load/edit behavior.
- [x] 4.2 Run the relevant frontend validation and backend test commands to verify create/edit flows and runtime resource-scope behavior.
