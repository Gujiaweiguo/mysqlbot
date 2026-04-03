# xpack-backend-compatibility Specification

## Purpose
Expose xpack-derived backend capabilities (startup, crypto, auth, license, permissions, prompt, config, file handling) through first-party provider contracts so that business modules no longer import `sqlbot_xpack` directly.
## Requirements
### Requirement: Backend xpack capabilities are accessed through first-party providers
The backend SHALL access xpack-derived runtime capabilities through first-party contracts and provider entrypoints instead of direct business-module imports of `sqlbot_xpack`.

#### Scenario: Startup and business modules use compat providers
- **WHEN** backend modules need startup, crypto, auth, license, permissions, prompt, config, or file-handling capabilities previously sourced from `sqlbot_xpack`
- **THEN** they SHALL call first-party provider modules owned by this repository rather than importing `sqlbot_xpack` directly in business code

### Requirement: Backend startup remains functional during migration
The backend SHALL preserve current startup behavior while startup hooks are migrated behind a first-party startup seam.

#### Scenario: Legacy-backed startup seam preserves boot behavior
- **WHEN** the application starts while the migration is still using a legacy adapter
- **THEN** startup initialization SHALL complete through the first-party startup provider without requiring `backend/main.py` to call `sqlbot_xpack` directly

### Requirement: Backend secret-handling contracts remain stable across implementation swaps
The backend SHALL preserve the current encrypt/decrypt contracts used by login, model credentials, datasource configuration, assistant configuration, and embedding configuration while capability providers are replaced.

#### Scenario: Existing callers keep their current crypto contract
- **WHEN** a backend caller uses the repository's public crypto or AES helper functions during migration
- **THEN** the caller SHALL continue using the same helper interface and SHALL not need to know whether a legacy adapter or first-party implementation serves the request
