## ADDED Requirements

### Requirement: Embedding configuration SHALL support Tencent Cloud provider type
The embedding configuration schema SHALL support `provider_type: tencent_cloud` as a valid provider type with corresponding authentication fields.

#### Scenario: Save Tencent Cloud configuration
- **WHEN** an administrator saves an embedding configuration with `provider_type: tencent_cloud`
- **THEN** the system SHALL accept `tencent_secret_id` and `tencent_secret_key` fields
- **AND** the system SHALL encrypt and store `tencent_secret_key` securely

#### Scenario: Load Tencent Cloud configuration
- **WHEN** an administrator views an existing Tencent Cloud embedding configuration
- **THEN** the system SHALL display the saved SecretId
- **AND** the system SHALL display a masked placeholder for SecretKey

### Requirement: Embedding admin UI SHALL display Tencent Cloud option
The embedding configuration UI SHALL include Tencent Cloud in the supplier dropdown when the provider type is `openai_compatible` or `tencent_cloud`.

#### Scenario: Display Tencent Cloud in supplier list
- **WHEN** an administrator opens the embedding configuration page
- **THEN** the supplier dropdown SHALL include Tencent Cloud (腾讯云) as an option
- **AND** the Tencent Cloud option SHALL display the Tencent Cloud icon

#### Scenario: Show Tencent Cloud specific fields
- **WHEN** an administrator selects Tencent Cloud as the supplier
- **THEN** the UI SHALL display SecretId and SecretKey input fields
- **AND** the UI SHALL display Region dropdown with available regions
- **AND** the UI SHALL display Model dropdown with available embedding models

### Requirement: Tencent Cloud SHALL be included in supported embedding suppliers
The backend SHALL include Tencent Cloud (id: 9) in the list of supported embedding suppliers.

#### Scenario: Backend accepts Tencent Cloud supplier
- **WHEN** the frontend sends an embedding configuration with `supplier_id: 9`
- **THEN** the backend SHALL accept the configuration
- **AND** the backend SHALL validate Tencent Cloud specific fields
