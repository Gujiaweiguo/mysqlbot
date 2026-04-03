## Why

The login experience currently has two opaque waiting periods: the login page can stay under a generic loading mask while authentication options are being resolved, and credential submission can take long enough that users are unsure whether their click was registered. That creates unnecessary uncertainty, repeat clicks, and a perception that the system is stuck even when it is still progressing normally.

## What Changes

- Define explicit user-visible waiting feedback for the login page bootstrap phase before the form is fully ready.
- Define explicit submission feedback for credential-based login actions so users can see that the request is in progress and cannot accidentally submit twice.
- Define post-login transition messaging for the period between successful credential validation and the point where the destination application view is ready.
- Keep this change focused on feedback and state communication only; do not bundle broader login performance refactors into the same scope.

## Capabilities

### New Capabilities
- `login-wait-feedback`: Defines required user-visible waiting feedback across login bootstrap, credential submission, and post-login transition states.

### Modified Capabilities
- None.

## Impact

- Affected files will likely include frontend login views under `frontend/src/views/login/**`, login-related routing/bootstrap code, and login-focused browser tests.
- User-visible behavior will change only in waiting/transition states; authentication rules and provider selection behavior should remain unchanged.
- Verification should focus on visible loading states, duplicate-submit prevention, and unchanged success/failure login outcomes.
