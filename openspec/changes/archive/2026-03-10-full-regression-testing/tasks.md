## 1. Regression Gate Definition

- [x] 1.1 Define mandatory gate order and pass/fail criteria for full regression
- [x] 1.2 Define stop-on-fail and waiver recording rules for release decision
- [x] 1.3 Document parallelizable vs strictly ordered gates

## 2. Fixture and Data Readiness

- [x] 2.1 Define `demo_sales` fixture contract (schemas, tables, minimum seed data)
- [x] 2.2 Define datasource metadata sync verification for fixture tables/fields
- [x] 2.3 Add deterministic precheck steps and expected outputs for fixture readiness

## 3. Functional and Failure-Path Validation

- [x] 3.1 Define key intelligent-query happy-path test cases against `demo_sales`
- [x] 3.2 Define 429/rate-limit regression cases and expected graceful behavior
- [x] 3.3 Define transient failure resilience checks (retry/backoff outcome validation)

## 4. Reporting and Adoption

- [x] 4.1 Define structured regression report template with required sections
- [x] 4.2 Define evidence collection requirements for every gate result
- [x] 4.3 Run one baseline regression using this change and publish the first report
