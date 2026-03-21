## Context

The current repository already uses a multi-stage Docker build, but several high-cost steps still sit behind coarse invalidation boundaries. The frontend builder copies the full `frontend/` tree before `npm install`, the SSR builder installs Node dependencies after copying source files, the backend stage still performs a second project sync after copying the full backend tree, and `.dockerignore` excludes only a narrow subset of local artifacts. In CI, both image build workflows force `--no-cache`, which eliminates the benefit of layer reuse entirely.

The user wants practical speed improvements now, not a runtime architecture rewrite. The existing all-in-one application image and Compose topology are already supported and should remain stable during this optimization pass.

## Goals / Non-Goals

**Goals:**
- Reduce Docker build-context size for normal source builds.
- Improve cache reuse for frontend, backend, and g2-ssr dependency installation.
- Make CI image builds reusable across repeated runs of the same workflows.
- Preserve the current all-in-one runtime behavior and deployment topology.

**Non-Goals:**
- Splitting FastAPI, MCP, or SSR into separate runtime containers.
- Changing operator-facing Compose topology or installer behavior in this change.
- Reworking application logic, startup order, or runtime ports.

## Decisions

### Decision 1: Keep the current all-in-one runtime topology

This change will optimize build performance without changing `start.sh`, Compose service boundaries, or the final runtime image contract.

**Why:**
- The bottleneck is build-time cache invalidation, not runtime process orchestration.
- Preserving runtime behavior keeps risk low and makes verification straightforward.

**Alternatives considered:**
- Split SSR into its own service now: rejected because it expands scope beyond the current performance issue.

### Decision 2: Make dependency manifests the cache boundary for Node stages

The frontend and g2-ssr builder stages will copy dependency manifests first, install dependencies, and only then copy the rest of the source.

**Why:**
- Most routine changes touch source files, not dependency manifests.
- This turns normal source edits into cheap rebuilds that reuse the dependency layer.

**Alternatives considered:**
- Keep current source-first copies and rely on package-manager cache alone: rejected because it still reruns dependency installation too often.

### Decision 3: Keep backend dependency installation separate from project source copy

The backend stage will install dependency layers from `pyproject.toml` and `uv.lock` before copying the full backend tree, then perform the project sync after source copy.

**Why:**
- This matches the existing intent while making the cache boundary explicit in the Dockerfile.
- It preserves the current runtime environment and package set without introducing a new packaging model.

**Alternatives considered:**
- Leave the backend stage unchanged: rejected because the current optimization is less explicit and less aligned with the other cache-friendly stages.

### Decision 4: Re-enable CI cache reuse with explicit Buildx cache scopes

The base-image workflow and app-image workflow will stop forcing `--no-cache` and will use Buildx cache import/export settings with distinct scopes.

**Why:**
- Repeated workflow runs should reuse prior layers instead of rebuilding from scratch.
- Separate scopes prevent the base image cache from colliding with the app image cache.

**Alternatives considered:**
- Remove `--no-cache` only: rejected because explicit cache persistence is more reliable across GitHub-hosted runners.

## Risks / Trade-offs

- **[Overly broad ignore rules]** → Keep `.dockerignore` focused on generated artifacts, caches, VCS metadata, and clearly unused large files.
- **[Node lockfile drift for g2-ssr]** → Generate and commit a lockfile so Docker can use deterministic `npm ci`.
- **[CI cache growth or collisions]** → Use separate cache scopes for base and app workflows.
- **[Behavioral drift during build refactor]** → Keep the same final runtime files, image stages, and entrypoint contract.

## Migration Plan

1. Add OpenSpec artifacts for the build optimization contract.
2. Tighten `.dockerignore` and reorder Dockerfile cache boundaries.
3. Generate and commit the `g2-ssr` lockfile required for deterministic `npm ci`.
4. Update both GitHub Actions image build workflows to use reusable cache settings.
5. Verify Docker config rendering and image builds still succeed with the optimized structure.

Rollback is straightforward: restore the previous Dockerfile, `.dockerignore`, lockfile, and workflow definitions if any cache-related regression appears.

## Open Questions

- None for this implementation pass.
