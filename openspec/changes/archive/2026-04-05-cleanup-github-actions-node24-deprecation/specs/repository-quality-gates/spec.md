## MODIFIED Requirements

### Requirement: Repository SHALL enforce stack-appropriate quality gates in CI
The repository SHALL define CI validation that covers both backend and frontend changes through stack-appropriate quality gates before merge. CI workflow action runtime configuration MUST remain on a supported GitHub Actions JavaScript runtime path so gate outcomes are not coupled to deprecated Node 20 execution behavior.

#### Scenario: Pull request changes frontend and backend code
- **WHEN** a pull request modifies backend Python files and frontend Vue or TypeScript files
- **THEN** CI runs the defined backend validation gates for the backend changes
- **AND** CI runs the defined frontend validation gates for the frontend changes

#### Scenario: CI quality gates run on supported JavaScript action runtime
- **WHEN** repository quality or regression workflows execute JavaScript-based GitHub Actions
- **THEN** workflow runtime configuration uses a supported Node execution path
- **AND** gate results are not dependent on deprecated Node 20 runtime behavior
