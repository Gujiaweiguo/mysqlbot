# mySQLBot Repo Sync Gate Guide

## Goal

`repo-sync` is an operational mirror-maintenance workflow, not a generic pull-request quality gate. Its job is to synchronize the upstream GitHub repository to the configured Gitee destination when maintainers explicitly need that sync path.

## Current Execution Policy

The `Synchronize to Gitee` workflow runs only in these contexts:

- push to `main`
- push to `master`
- manual `workflow_dispatch`

It does **not** run for ordinary feature-branch pushes or pull requests.

## Why It Is Not a Normal PR Blocker

Repository synchronization depends on external infrastructure that is outside the scope of most application changes:

- Gitee credentials
- Gitee repository existence and permissions
- SSH private key validity
- external network access to Gitee

Because of that, `repo-sync` should not be treated as a required check for everyday pull requests unless the team explicitly decides to make repository mirroring part of the normal review contract.

## Current Targets and Dependencies

- Source: `github/dataease`
- Static repository list: `SQLBot`
- Destination: `gitee/fit2cloud-feizhiyun`
- Required secrets:
  - `GITEE_PRIVATE_KEY`
  - `GITEE_TOKEN`

## Preflight Validation

Before the mirror action runs, the workflow now validates:

- `GITEE_PRIVATE_KEY` exists
- `GITEE_TOKEN` exists
- `GITEE_PRIVATE_KEY` can be parsed as a valid SSH private key

This turns silent external failures into explicit prerequisite errors.

## Ownership

Recommended ownership for this gate:

- **Workflow policy:** repository maintainers
- **Gitee credentials and mirror target access:** release/infrastructure maintainers with Gitee admin access

Application contributors should generally not be expected to diagnose or repair Gitee credential issues as part of ordinary feature work.

## How to Interpret Failures

### Failure: missing `GITEE_PRIVATE_KEY`

Meaning: the workflow cannot authenticate to the destination using SSH.

Action:
- confirm the repository secret exists
- confirm the stored secret is the full private key content

### Failure: missing `GITEE_TOKEN`

Meaning: the workflow cannot call the Gitee API to create or inspect the destination repository.

Action:
- confirm the repository secret exists
- confirm the token is still valid and has the required permissions

### Failure: invalid SSH private key

Meaning: the secret is present, but its content is malformed or no longer parsable by SSH tooling.

Action:
- rotate and re-save the private key secret
- verify the stored value preserves line breaks correctly

### Failure: `401 Unauthorized` from Gitee API

Meaning: the token exists but is not accepted by Gitee.

Action:
- rotate `GITEE_TOKEN`
- verify the token belongs to the expected account and still has the needed scope

### Failure: `Permission denied (publickey)`

Meaning: the mirror action reached SSH push, but the destination rejected the configured key.

Action:
- confirm the public key corresponding to `GITEE_PRIVATE_KEY` is registered in the destination Gitee account
- confirm the account has write access to `fit2cloud-feizhiyun/SQLBot`

## Recovery Path

1. Identify whether the failure is a **preflight failure** or a **mirror execution failure**
2. If preflight fails, fix repository secrets first
3. If the Gitee API returns authorization errors, rotate the token
4. If SSH push fails, verify the registered public key and repository permissions
5. Re-run the workflow manually after repairing credentials or access

## Branch Protection Recommendation

Do not add `repo-sync` as a required check for normal pull requests unless your team intentionally wants Gitee mirroring to be part of the standard merge contract.
