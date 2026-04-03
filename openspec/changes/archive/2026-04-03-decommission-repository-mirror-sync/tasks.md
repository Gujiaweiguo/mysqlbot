## 1. Retire external mirror workflows

- [x] 1.1 Remove or disable `.github/workflows/sync2gitee.yml` so GitHub-to-Gitee sync is no longer an active repository-maintenance path
- [x] 1.2 Remove or disable `.github/workflows/sync_to_cnb.yml` if CNB sync is also no longer an intentionally supported path

## 2. Update repository sync contract

- [x] 2.1 Update `openspec/specs/repository-sync-gate/spec.md` to reflect decommissioned or non-operational-by-default mirror behavior
- [x] 2.2 Update `docs/repo-sync-gate.md` to explain that external mirror sync is retired and how to interpret historical repo-sync failures
- [x] 2.3 Update repository-level references such as `README.md` so they no longer present repo sync as an active maintenance path

## 3. Validate repository health after retirement

- [x] 3.1 Check for any branch protection rules, required checks, or references that still assume `repo-sync` must exist
- [x] 3.2 Verify the repository no longer reports mirror-related failures as part of normal `main` maintenance
