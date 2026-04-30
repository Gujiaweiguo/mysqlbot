## Why

The assistant application setup currently lacks explicit workspace and datasource configuration for both basic applications and advanced applications, which prevents administrators from constraining assistant scope to the intended data boundary. We need this now so assistant publishing can align with workspace-level isolation and allow one assistant to be bound to multiple approved datasources without manual workarounds.

## What Changes

- Add assistant application configuration support for selecting one or more workspaces when creating or editing both basic applications and advanced applications.
- Add assistant application configuration support for selecting one or more datasources within the permitted scope for both basic applications and advanced applications.
- Define persistence, load, and update behavior so previously selected workspaces and datasources are returned consistently in assistant configuration flows.
- Define validation rules that reject invalid, disabled, or out-of-scope workspace and datasource selections.
- Define the dependency behavior between workspace selection and datasource selection, including how selectable datasources are constrained by the selected workspaces.

## Capabilities

### New Capabilities
- `assistant-workspace-datasource-selection`: Defines how basic and advanced assistant applications load, save, validate, and enforce multi-select workspace and datasource configuration.

### Modified Capabilities
- None.

## Impact

- Affected backend areas likely include assistant application configuration APIs, assistant persistence models, workspace/datasource lookup and validation services, and any runtime assistant scope resolution path.
- Affected frontend areas likely include the assistant application forms for basic applications and advanced applications, especially field loading, cascading selection, and edit-state rendering.
- Verification will need to cover create/edit flows, multi-select persistence, invalid-scope rejection, and consistency between stored configuration and runtime assistant availability.
