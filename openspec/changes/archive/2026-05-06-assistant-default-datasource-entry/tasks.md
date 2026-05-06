## 1. Assistant configuration

- [x] 1.1 Restore or add assistant/embedded configuration controls for direct entry with an explicit default datasource.
- [x] 1.2 Persist and validate the configured default datasource in assistant settings without changing main mysqlbot chat configuration behavior.

## 2. Assistant chat entry behavior

- [x] 2.1 Update assistant start-chat orchestration so direct entry creates a chat bound to the configured default datasource.
- [x] 2.2 Add failure handling for missing, deleted, or inaccessible configured default datasources.

## 3. Datasource visibility and switching

- [x] 3.1 Show the active datasource in assistant and embedded chat sessions started from direct entry.
- [x] 3.2 Add a datasource switch action that reuses the datasource picker flow for assistant and embedded chat.
- [x] 3.3 Ensure switching datasource creates a new chat session and preserves the original session unchanged.

## 4. Validation

- [x] 4.1 Add or update regression coverage for assistant direct entry with a configured default datasource.
- [x] 4.2 Add or update regression coverage for datasource switching creating a new assistant chat session.
- [x] 4.3 Run the relevant frontend, backend, and regression validation commands for the touched areas.
