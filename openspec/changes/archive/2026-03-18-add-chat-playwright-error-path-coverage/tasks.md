## 1. Error-path fixture support

- [x] 1.1 Extend the existing Playwright chat fixtures so the mocked `/api/v1/chat/question` stream can emit a deterministic `error` event after submission starts
- [x] 1.2 Add or update any stable selector hook needed to assert the rendered chat error state without depending on brittle DOM structure

## 2. Browser coverage

- [x] 2.1 Add a Playwright smoke test for the primary chat streamed error path using the existing baseline harness
- [x] 2.2 Assert preserved user question, visible error outcome, and cleared thinking/streaming state for the failed response

## 3. Verification and docs

- [x] 3.1 Update `frontend/e2e/README.md` so the error-path test is part of the covered baseline and any remaining deferred scenarios stay explicit
- [x] 3.2 Run the targeted Playwright chat suite in headless mode
- [x] 3.3 Run frontend lint and build checks after the error-path extension lands
