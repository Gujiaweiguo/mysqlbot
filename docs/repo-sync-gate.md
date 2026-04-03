# mySQLBot Repository Sync Retirement Guide

## Goal

External repository mirror sync is retired in this repository. GitHub is the source of truth, and normal repository health no longer depends on keeping Gitee or CNB mirrors updated.

## Current Policy

- The repository does **not** maintain GitHub-to-Gitee sync as a normal `main`/`master` workflow.
- The repository does **not** treat external mirror sync as part of the standard quality or release contract.
- If mirror sync is ever needed again, it should be reintroduced through an explicit change rather than assumed from historical behavior.

## What Changed

Historically, this repository contained mirror workflows for Gitee and CNB. Those paths were retired because they added external-platform failures, credentials, and operational noise to the repository without serving an active maintainer need.

As a result:

- missing Gitee or CNB credentials are no longer part of normal repository health
- routine pushes should not produce mirror-related failures
- contributors should not be asked to diagnose external mirror infrastructure for everyday development work

## Historical Failures

Older GitHub Actions history may still show `repo-sync` or other mirror-related failures. Those runs belong to the retired mirror-maintenance path and should be read as historical operational context, not as evidence that current application changes are unhealthy.

## Historical Failure Meanings

The following failure modes apply only to historical runs from before mirror retirement:

### Failure: missing `GITEE_PRIVATE_KEY`

Meaning: the historical workflow could not authenticate to the Gitee destination over SSH.

### Failure: missing `GITEE_TOKEN`

Meaning: the historical workflow could not call the Gitee API to create or inspect the destination repository.

### Failure: invalid SSH private key

Meaning: the historical secret content was malformed or no longer parsable by SSH tooling.

### Failure: `401 Unauthorized` from Gitee API

Meaning: the historical Gitee token existed but was not accepted by the destination platform.

### Failure: `Permission denied (publickey)`

Meaning: the historical mirror action reached SSH push, but the destination rejected the configured key.

## Maintainer Guidance

- Do not treat `repo-sync` as a required check for current pull requests or routine `main` maintenance.
- If GitHub branch protection still references historical mirror checks, remove those required checks from repository settings.
- If repository or organization secrets such as `GITEE_PRIVATE_KEY`, `GITEE_TOKEN`, or `CNB_PASSWORD` still exist only for the retired workflows, they can be removed from GitHub settings as a separate cleanup step.

## Reintroduction Policy

If the project later decides to restore a mirror destination, define that workflow, ownership, credentials, and gating policy through a new explicit OpenSpec change before re-enabling automation.
