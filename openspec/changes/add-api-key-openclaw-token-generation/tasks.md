## 1. API key token workflow

- [x] 1.1 Add API Key UI affordances to generate an OpenClaw token from an existing API key row.
- [x] 1.2 Implement reveal and copy actions for the raw JWT token artifact and the `sk <jwt>` header-style value.
- [x] 1.3 Add UI guidance that explains which generated artifact belongs in OrchestratorAgent config versus direct request headers.

## 2. Token generation path

- [x] 2.1 Add the selected token-generation implementation path so the UI can derive JWT output without changing the external auth contract.
- [x] 2.2 Keep generated token state ephemeral and scoped to explicit user interaction rather than storing derived tokens as persistent backend data.

## 3. Onboarding and validation

- [x] 3.1 Update OpenClaw onboarding or assistant wording so operator-facing guidance matches the generated token workflow.
- [x] 3.2 Validate the generated output against the existing `X-SQLBOT-ASK-TOKEN` + `sk` contract and verify the relevant frontend quality checks pass.
