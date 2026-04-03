# demo-fixture-validation Specification

## Purpose
Verify that the `demo_sales` fixture schema, required tables, and seed data exist and that datasource metadata is synchronized before intelligent-query regression tests execute.
## Requirements
### Requirement: Deterministic demo fixture availability
The regression process SHALL validate that the `demo_sales` fixture schema exists with required tables and seed data before intelligent-query tests are executed.

#### Scenario: Fixture precheck success
- **WHEN** the fixture precheck runs
- **THEN** it confirms schema `demo_sales`, required tables, and minimum row counts are present

### Requirement: Fixture metadata synchronization
The regression process MUST verify that datasource metadata used by intelligent-query features is synchronized with the fixture tables and columns.

#### Scenario: Metadata readiness check
- **WHEN** fixture validation completes
- **THEN** datasource table/field metadata reflects current `demo_sales` objects and is eligible for NL2SQL testing
