# third-party-user-provisioning-settings Specification

## Purpose
Allow administrators to configure auto-creation behavior, default workspace, and default role for users arriving through external authentication or platform-integration flows.
## Requirements
### Requirement: Administrators can control third-party auto-user creation defaults
The system SHALL allow administrators to configure whether externally authenticated users are auto-created and which default workspace and role they receive.

#### Scenario: Third-party provisioning settings page loads current defaults
- **WHEN** an administrator opens the third-party platform settings section
- **THEN** the backend SHALL return the current auto-create flag, default workspace, and default role settings

### Requirement: Third-party provisioning defaults affect new external users
The system SHALL apply the configured defaults when creating new users from supported external authentication or platform-integration flows.

#### Scenario: External user is auto-created after successful external authentication
- **WHEN** an enabled external authentication or platform integration creates a new local user
- **THEN** the system SHALL assign the configured default workspace and role to that user

### Requirement: Provisioning settings remain isolated from unrelated admin configuration
The system SHALL store and apply third-party provisioning defaults without requiring administrators to manually update unrelated authentication or appearance settings.

#### Scenario: Administrator updates third-party provisioning defaults
- **WHEN** an administrator saves changes to auto-create behavior, default workspace, or default role
- **THEN** the system SHALL persist those settings and leave unrelated admin configuration unchanged
