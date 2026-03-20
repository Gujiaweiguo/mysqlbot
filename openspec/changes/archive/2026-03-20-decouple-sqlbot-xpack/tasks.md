## 1. Baseline and compatibility setup

- [x] 1.1 Add characterization tests for startup hooks, backend crypto/AES wrappers, and frontend `LicenseGenerator` contract behavior.
- [x] 1.2 Introduce `backend/common/xpack_compat/` and `frontend/src/xpack-compat/` with contracts, providers, and legacy adapters.
- [x] 1.3 Route backend startup behavior in `backend/main.py` through a first-party startup provider.

## 2. Crypto and frontend facade migration

- [x] 2.1 Route `backend/common/utils/crypto.py` and `backend/common/utils/aes_crypto.py` through first-party provider entrypoints.
- [x] 2.2 Route frontend login, model-configuration, and route-bootstrap calls through the local `LicenseGenerator` compatibility facade.
- [x] 2.3 Add parity and mixed-mode tests that verify frontend/backend encryption compatibility during migration.

## 3. First-party replacement of core runtime capabilities

- [x] 3.1 Implement first-party backend crypto/AES services with compatibility for existing stored secrets and protected configuration.
- [x] 3.2 Introduce first-party auth/logout seams and migrate current xpack-backed logout integration behind repository-owned providers.
- [x] 3.3 Introduce a first-party license facade and preserve temporary compatibility for existing xpack static bootstrap assets.

## 4. First-party replacement of business-domain capabilities

- [x] 4.1 Migrate datasource permissions to first-party models/providers with row and column parity tests.
- [x] 4.2 Migrate custom prompt lookups and related enums to first-party chat-domain services.
- [x] 4.3 Migrate parameter/config flows and file utility behavior to first-party system/common modules.

## 5. Dependency removal and validation

- [x] 5.1 Remove remaining direct `sqlbot_xpack` imports from business modules and keep the legacy dependency isolated to migration adapters only.
- [x] 5.2 Remove the `sqlbot-xpack` dependency, legacy adapters, test stubs, and build/runtime assumptions after parity validation succeeds.
- [x] 5.3 Validate backend startup, frontend bootstrap, login, model configuration, datasource configuration, permissions, tests, and build flows without the external package installed.
