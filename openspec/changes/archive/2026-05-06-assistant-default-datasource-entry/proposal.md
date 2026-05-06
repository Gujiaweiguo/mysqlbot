## Why

Assistant and embedded chat already support direct entry without forcing an upfront datasource picker, but that path currently behaves as an unbound chat rather than a guided default-datasource experience. In multi-datasource workspaces, we need a safer assistant-scoped entry model that preserves fast first-use access while keeping datasource choice explicit and reversible.

## What Changes

- Add assistant/embedded configuration support for an explicit default datasource used when entering chat directly.
- Change assistant/embedded direct-entry behavior so the chat starts with the configured default datasource instead of an unbound datasource-less session.
- Show the active datasource in assistant/embedded chat when default direct entry is enabled and provide a datasource switch action.
- Require datasource switching in assistant/embedded chat to open a new chat session rather than mutating an existing session in place.
- Keep the main mysqlbot chat page behavior unchanged: standard chat still requires explicit datasource selection before starting a session.

## Capabilities

### New Capabilities
- `assistant-default-datasource-entry`: Define assistant and embedded chat behavior for configured default datasource entry, visible datasource state, and switch-to-new-session handling.

### Modified Capabilities
- `chat-critical-journeys`: Extend critical chat coverage to include the assistant default-datasource direct-entry and datasource-switch journey.

## Impact

- Affected frontend areas: assistant/embedded configuration UI, assistant store state, chat entry shell, and datasource switch controls.
- Affected backend areas: assistant configuration persistence and assistant chat start behavior when a default datasource is configured.
- Affected validation: assistant/embedded regression coverage for direct entry and datasource switching.
