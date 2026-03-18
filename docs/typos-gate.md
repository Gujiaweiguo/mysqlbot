# mySQLBot Typos Gate Guide

## Goal

The typos gate is meant to catch **new spelling regressions introduced by the current pull request**. It is not intended to force every PR to clean up the repository's full historical typo backlog.

## Current Behavior

- On `pull_request`, the `Typos Check` workflow scans only changed code/config text files in the first rollout.
- On `workflow_dispatch`, maintainers can run a full-repository spelling audit by choosing `scope=full`.
- Repository vocabulary and reviewed exceptions live in `.typos.toml`.

## What Counts as a Blocking Failure

A PR should fail the typos gate when:

- a newly changed file introduces a misspelled word,
- a changed identifier contains an unapproved typo, or
- a contributor adds new text that requires a reviewed allowlist entry but does not update `.typos.toml`.

A PR should not fail only because unrelated historical typos still exist in untouched files or in untouched documentation backlog.

## How to Add Approved Vocabulary

Use `.typos.toml` and keep the change explicit in review.

- Add prose terms under `[default.extend-words]`
- Add code symbols or identifiers under `[default.extend-identifiers]`
- Add file or directory exclusions under `[files.extend-exclude]` only when the content is generated, vendored, or otherwise not practical to govern at PR time

Good candidates for allowlisting:

- product names like `mySQLBot`
- internal service names like `gosqlbot`
- established platform terms like `xpack`

Bad candidates for allowlisting:

- obvious misspellings that happen to exist historically
- one-off typos in docs or comments
- words that should be corrected in source instead of normalized in config

## How Maintainers Should Interpret Failures

1. Check whether the reported file was changed by the current PR.
2. If yes, determine whether the token is:
   - a real typo to fix, or
   - a legitimate project/domain term that belongs in `.typos.toml`
3. If the failure comes from a manual `scope=full` run, treat it as maintenance backlog unless the change explicitly aims to clean historical typos.

## Maintenance Path for Historical Debt

Historical repository typo debt, especially documentation-heavy backlog, should be reviewed through manual full-repository scans rather than unrelated blocking PR failures.

Recommended workflow:

1. Run `Typos Check` manually with `scope=full`
2. Group findings into:
   - project vocabulary to allowlist
   - real historical typos to clean in batches
3. Fix historical typos in small, reviewable cleanup PRs

## Review Policy

- Prefer fixing the source text over adding an allowlist entry.
- Every new allowlist entry should be reviewable and justified by project vocabulary, not convenience.
- Avoid broad exclusions unless the content is generated or outside normal maintenance boundaries.
