## Why

Source-based Docker deployments are slower than they need to be because small frontend, backend, or SSR code changes invalidate large build sections and force repeated dependency installation. We need a cache-friendlier build contract so local source builds and CI image builds finish faster without changing the current all-in-one runtime topology.

## What Changes

- Tighten the Docker build context so generated files, caches, repository metadata, and large local-only assets do not participate in routine image builds.
- Reorder frontend and g2-ssr image layers so dependency installation is isolated from normal source edits and can reuse cache correctly.
- Refine backend dependency installation so dependency resolution remains separated from application source changes while preserving the current runtime contents.
- Replace forced cold CI image builds with reusable Buildx cache settings for the base image and app image workflows.
- Keep the current bundled runtime behavior for FastAPI, MCP, and SSR inside one application image.

## Capabilities

### New Capabilities
- `docker-build-optimization`: Defines the repository's supported Docker build caching, build-context minimization, and CI image cache reuse behavior.

### Modified Capabilities
- None.

## Impact

- Affected files include `.dockerignore`, `Dockerfile`, `g2-ssr/package-lock.json`, and `.github/workflows/build_and_push.yml` plus `.github/workflows/build_base_and_push.yml`.
- Docker source builds should reuse dependency layers more effectively after frontend, backend, or SSR source-only changes.
- CI image builds should stop forcing `--no-cache` and start persisting reusable Buildx cache state.
- Runtime topology, exposed ports, startup ordering, and the existing Compose service shape remain unchanged.
