# docker-build-optimization Specification

## Purpose
TBD - created by archiving change optimize-docker-build-deployment. Update Purpose after archive.
## Requirements
### Requirement: Docker source builds SHALL minimize unrelated build context input
The repository SHALL exclude generated artifacts, dependency directories, cache directories, repository metadata, and unrelated large local files from the Docker build context used by source-based image builds.

#### Scenario: Local source build ignores non-runtime artifacts
- **WHEN** a Docker build is started from the repository root
- **THEN** generated dependency directories, test caches, editor metadata, and unrelated large local files SHALL be excluded from the build context

### Requirement: Frontend and SSR builders SHALL isolate dependency installation from source edits
The Docker build contract SHALL install frontend and g2-ssr Node dependencies from manifest files before copying the rest of each source tree so source-only edits can reuse the dependency layer.

#### Scenario: Frontend source change reuses dependency layer
- **WHEN** frontend application source changes but `frontend/package.json` and `frontend/package-lock.json` do not change
- **THEN** the Docker build SHALL be able to reuse the cached frontend dependency installation layer

#### Scenario: SSR source change reuses dependency layer
- **WHEN** g2-ssr source changes but its dependency manifest and lockfile do not change
- **THEN** the Docker build SHALL be able to reuse the cached g2-ssr dependency installation layer

### Requirement: Backend builder SHALL separate dependency installation from project source copy
The Docker build contract SHALL install backend dependencies from `backend/pyproject.toml` and `backend/uv.lock` before copying the full backend source tree, then install the project after source copy.

#### Scenario: Backend source change preserves dependency cache
- **WHEN** backend application code changes but dependency manifests do not change
- **THEN** the Docker build SHALL reuse the cached backend dependency layer and only rerun the post-copy project sync step

### Requirement: CI image builds SHALL reuse Buildx cache across repeated runs
The repository's GitHub Actions image build workflows SHALL use reusable Buildx cache import/export settings instead of forcing every build to run with a cold cache.

#### Scenario: Repeat app-image workflow run uses prior cache
- **WHEN** the app image workflow runs again for unchanged or partially changed inputs
- **THEN** the workflow SHALL be configured to import and export a persistent Buildx cache scope for the app image build

#### Scenario: Repeat base-image workflow run uses prior cache
- **WHEN** the base image workflow runs again for unchanged or partially changed inputs
- **THEN** the workflow SHALL be configured to import and export a persistent Buildx cache scope for the base image build

