# main-spec-purpose-hygiene Specification

## Purpose
Ensure canonical OpenSpec capability specs keep explicit, requirement-aligned Purpose summaries instead of archive-time placeholder text.
## Requirements
### Requirement: Canonical spec purposes are explicit
Canonical OpenSpec capability specs SHALL provide an explicit `Purpose` summary in the main spec and SHALL NOT retain archive-time placeholder text after the source change is archived.

#### Scenario: Archived capability remains in the main spec set
- **WHEN** a capability spec exists under `openspec/specs/<capability>/spec.md`
- **THEN** its `Purpose` section contains a concise summary of the capability intent
- **AND** it does not contain the archive placeholder text created during sync/archive

### Requirement: Purpose summaries stay aligned with capability requirements
Purpose summaries in canonical specs SHALL describe the actual capability intent reflected by the current requirement body and SHALL NOT introduce behavior not supported by the spec.

#### Scenario: Maintainer updates placeholder purpose text
- **WHEN** a maintainer replaces a placeholder `Purpose` in a canonical spec
- **THEN** the replacement summary is grounded in the capability's archived source change and current requirements
- **AND** the maintainer does not alter requirement meaning as part of the purpose-only cleanup
