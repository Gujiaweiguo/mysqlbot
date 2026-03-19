## ADDED Requirements

### Requirement: System SHALL support Tencent Cloud native Embedding Provider
The system SHALL provide a Tencent Cloud native Embedding Provider that uses SecretId/SecretKey authentication and calls the Tencent Cloud LKEAP GetEmbedding API.

#### Scenario: Configure Tencent Cloud embedding provider
- **WHEN** an administrator selects Tencent Cloud as the embedding provider type
- **THEN** the system SHALL display configuration fields for SecretId, SecretKey, Region, and Model
- **AND** the system SHALL save the configuration with SecretKey encrypted

#### Scenario: Validate Tencent Cloud credentials
- **WHEN** an administrator validates the Tencent Cloud embedding configuration
- **THEN** the system SHALL call the Tencent Cloud GetEmbedding API with the provided credentials
- **AND** the system SHALL return success if the API call succeeds
- **AND** the system SHALL return a descriptive error if the API call fails

### Requirement: Tencent Cloud Embedding Provider SHALL use official SDK
The Tencent Cloud Embedding Provider SHALL use the `tencentcloud-sdk-python-lkeap` SDK for API calls and signature authentication.

#### Scenario: API call uses correct authentication
- **WHEN** the system makes an embedding request to Tencent Cloud
- **THEN** the system SHALL use Tencent Cloud Signature v3 authentication
- **AND** the system SHALL include the correct SecretId and signed request

### Requirement: Tencent Cloud Embedding Provider SHALL support multiple regions
The system SHALL allow administrators to configure the Tencent Cloud region for embedding API calls.

#### Scenario: Use default region
- **WHEN** an administrator does not specify a region
- **THEN** the system SHALL use `ap-guangzhou` as the default region

#### Scenario: Use custom region
- **WHEN** an administrator specifies a region (e.g., `ap-shanghai`)
- **THEN** the system SHALL use the specified region for API calls

### Requirement: Tencent Cloud Embedding Provider SHALL support available models
The system SHALL support Tencent Cloud LKEAP embedding models.

#### Scenario: List available models
- **WHEN** an administrator views the model dropdown for Tencent Cloud
- **THEN** the system SHALL display available embedding models: `lke-text-embedding-v1`, `lke-text-embedding-v2`, `youtu-embedding-llm-v1`

#### Scenario: Use selected model
- **WHEN** an administrator selects a model
- **THEN** the system SHALL use that model for all embedding requests
