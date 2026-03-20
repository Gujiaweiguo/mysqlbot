## Why

`sqlbot_xpack` is currently a compiled external dependency with no editable source in this repository, but it participates in startup hooks, encryption, frontend bootstrap, and several higher-level business flows. That makes production issues hard to diagnose, blocks safe feature extension, and leaves core behavior coupled to a closed implementation that the team cannot patch locally.

## What Changes

- Introduce first-party backend compatibility contracts and provider entrypoints for xpack-derived capabilities instead of letting business modules import `sqlbot_xpack` directly.
- Introduce a first-party frontend facade for `LicenseGenerator` and related xpack static/bootstrap behavior so application code no longer depends on a vendor global directly.
- Migrate startup hooks, crypto/AES wrappers, auth/logout seams, license checks, permissions access, custom prompts, config flows, and file utilities behind phased first-party boundaries.
- Preserve existing runtime behavior during migration through legacy adapters, compatibility tests, and phased cutover controls.
- Remove the `sqlbot-xpack` dependency and related build/runtime assumptions only after all runtime paths have first-party implementations.

## Capabilities

### New Capabilities
- `xpack-backend-compatibility`: Backend runtime capabilities currently sourced from `sqlbot_xpack` are exposed through first-party contracts, providers, and legacy adapters.
- `xpack-frontend-compatibility`: Frontend xpack-dependent behavior is accessed through a first-party facade that preserves current login, model-configuration, and route-bootstrap behavior during migration.
- `xpack-dependency-removal`: The system supports phased migration away from `sqlbot_xpack` and reaches an end state where runtime and build paths no longer require the external package.

### Modified Capabilities
<!-- None. This change introduces new migration and compatibility contracts rather than changing requirements in an existing capability spec. -->

## Impact

- Affected backend entrypoints: `backend/main.py`, `backend/common/utils/crypto.py`, `backend/common/utils/aes_crypto.py`
- Affected backend domains: auth/logout, license checks, datasource permissions, custom prompts, parameter/config flows, file handling
- Affected frontend areas: `frontend/src/router/watch.ts`, `frontend/src/api/login.ts`, `frontend/src/api/system.ts`, and `LicenseGenerator`-dependent pages/stores
- Affected build/runtime assets: `backend/pyproject.toml`, `backend/uv.lock`, Docker build/runtime hooks, xpack static compatibility assets, and test stubs
- Operational impact: enables maintainable first-party ownership of previously closed-source runtime behavior while reducing long-term dependency and debugging risk
