## 1. OpenSpec and build context

- [x] 1.1 Finalize the Docker build optimization change artifacts for proposal, design, specs, and implementation tasks
- [x] 1.2 Expand `.dockerignore` so source builds exclude generated dependencies, caches, repository metadata, and unrelated large local files

## 2. Docker build layering

- [x] 2.1 Refactor the frontend Docker stage to copy manifests first, install with lockfile-based Node commands, then copy source and build assets
- [x] 2.2 Refactor the backend Docker stage so dependency installation is clearly separated from the full backend source copy while preserving the current runtime contents
- [x] 2.3 Add a deterministic `g2-ssr` lockfile and refactor the SSR Docker stage to install dependencies before copying source files

## 3. CI cache reuse

- [x] 3.1 Update the app image GitHub Actions workflow to stop forcing cold builds and to persist a dedicated Buildx cache scope
- [x] 3.2 Update the base image GitHub Actions workflow to stop forcing cold builds and to persist a dedicated Buildx cache scope

## 4. Verification

- [x] 4.1 Validate the OpenSpec change state is apply-ready with completed artifacts
- [x] 4.2 Validate Docker-related file changes with targeted config/build checks so the optimized build contract remains consistent
