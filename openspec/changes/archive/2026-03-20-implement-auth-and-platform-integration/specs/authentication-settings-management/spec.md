## ADDED Requirements

### Requirement: Administrators can manage authentication provider settings
The system SHALL allow administrators to view and manage authentication provider configurations for supported provider types such as LDAP, OIDC, CAS, and OAuth2 through first-party APIs.

#### Scenario: Authentication settings page loads configured providers
- **WHEN** an administrator opens the authentication settings page
- **THEN** the backend SHALL return provider records with their identifiers, provider names, configuration payloads, validation state, and enablement state

### Requirement: Authentication providers can be validated and enabled independently
The system SHALL support testing provider configuration and toggling provider enablement without requiring full login-flow rewrites in the admin page.

#### Scenario: Administrator validates a provider configuration
- **WHEN** an administrator triggers a provider validation action for a configured authentication provider
- **THEN** the system SHALL execute provider-specific validation logic and return whether the configuration is valid

#### Scenario: Administrator enables a valid provider
- **WHEN** an administrator enables a provider that has passed validation
- **THEN** the system SHALL persist the enablement state and expose that state to login/bootstrap consumers

### Requirement: Login page reflects configured authentication providers
The system SHALL expose authentication provider status in a form that allows the login page to present the currently supported authentication methods.

#### Scenario: Login bootstrap reads provider status
- **WHEN** the login page loads its authentication bootstrap data
- **THEN** the system SHALL return provider availability derived from persisted configuration rather than hardcoded placeholder values
