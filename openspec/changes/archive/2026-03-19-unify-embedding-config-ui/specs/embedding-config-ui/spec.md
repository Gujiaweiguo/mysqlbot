## ADDED Requirements

### Requirement: Embedding Configuration UI SHALL use shared supplier list
The system SHALL provide the Embedding Configuration UI that uses the shared `supplierList` from `@/entity/supplier.ts`, filtered to only include embedding-capable suppliers.

#### Scenario: Display supplier list with icons
- **WHEN** an administrator opens the Embedding Configuration page
- **THEN** the UI SHALL display suppliers from the shared supplier list with their icons
- **AND** the UI SHALL only show suppliers that support OpenAI-compatible embeddings API

#### Scenario: Select supplier updates base URL
- **WHEN** an administrator selects a supplier from the dropdown
- **THEN** the base URL field SHALL be automatically populated with the supplier's default API domain

### Requirement: Embedding Configuration UI SHALL provide model dropdown
The system SHALL provide a model selection dropdown in the Embedding Configuration UI that shows available embedding models for the selected supplier.

#### Scenario: Display model options for selected supplier
- **WHEN** an administrator selects a supplier
- **THEN** the model dropdown SHALL be populated with embedding models for that supplier
- **AND** the model dropdown SHALL be filterable and allow custom input

#### Scenario: Custom model name input
- **WHEN** an administrator types a custom model name not in the list
- **THEN** the system SHALL accept the custom model name

### Requirement: Embedding Configuration UI SHALL display Chinese labels correctly
The system SHALL ensure all labels in the Embedding Configuration UI display in the user's selected language (Chinese by default).

#### Scenario: Display Chinese labels
- **WHEN** an administrator with Chinese locale opens the Embedding Configuration page
- **THEN** all labels SHALL display in Chinese
- **AND** labels SHALL use correct i18n keys matching the translation files

#### Scenario: Supplier names display in Chinese
- **WHEN** an administrator views the supplier dropdown
- **THEN** supplier names SHALL display in the administrator's selected language using `i18nKey` from supplier list

### Requirement: Backend SHALL provide embedding model list API
The system SHALL provide a backend API endpoint that returns available embedding models for a given supplier.

#### Scenario: Fetch embedding models for supplier
- **WHEN** the frontend requests `/system/embedding/models?supplier_id={id}`
- **THEN** the backend SHALL return a list of embedding model names for that supplier
- **AND** the response SHALL include model names suitable for embedding operations
