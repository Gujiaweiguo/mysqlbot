## ADDED Requirements

### Requirement: Login bootstrap SHALL surface an explicit waiting state
The login experience SHALL show a user-visible waiting state while authentication bootstrap checks are still determining whether the login form or alternate authentication path can be displayed.

#### Scenario: User opens login page during bootstrap checks
- **WHEN** the login entry flow is still resolving authentication availability or redirect behavior
- **THEN** the UI shows an explicit waiting message instead of a silent generic pause
- **AND** the user can distinguish that the system is preparing login options rather than being unresponsive

### Requirement: Credential submission SHALL show in-progress feedback and prevent duplicate submits
Credential-based login flows SHALL show in-progress feedback on submission and prevent repeated submit actions while the current login attempt is still pending.

#### Scenario: User submits username and password
- **WHEN** the user starts a credential login request
- **THEN** the UI shows an in-progress state on the login action
- **AND** repeated login submits are prevented until the request resolves

### Requirement: Post-login transition SHALL surface entry-in-progress feedback
The login experience SHALL show a user-visible transition state after successful authentication while the application is still preparing the destination experience.

#### Scenario: Authentication succeeds before destination view is ready
- **WHEN** the login request succeeds but the destination application view is still loading required bootstrap state
- **THEN** the UI shows an explicit “entering the system” style transition state
- **AND** users are not left without feedback between successful login and destination readiness

### Requirement: Login wait feedback SHALL avoid fake numeric progress
The login experience SHALL communicate waiting through truthful stage-based messaging or loading states rather than numeric progress values that are not backed by real measurable progress.

#### Scenario: Login includes variable-latency async work
- **WHEN** login bootstrap or post-login initialization takes variable time
- **THEN** the UI uses stage text or indeterminate loading indicators
- **AND** the system does not display misleading percentage progress for those waits
