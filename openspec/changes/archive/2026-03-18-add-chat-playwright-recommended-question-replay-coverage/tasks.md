## 1. Replay fixture and selector support

- [x] 1.1 Write the failing Playwright replay spec for clicking a visible recommended question from an already loaded successful chat
- [x] 1.2 Extend the existing Playwright chat fixtures with deterministic replay support for the follow-up response
- [x] 1.3 Add or confirm the smallest stable selector hook needed for the recommendation trigger

## 2. Browser coverage

- [x] 2.1 Make the recommended-question replay Playwright spec pass using the existing baseline harness
- [x] 2.2 Assert replayed user turn visibility, follow-up assistant result visibility, and cleared thinking or streaming state

## 3. Verification and docs

- [x] 3.1 Update `frontend/e2e/README.md` so recommended-question replay is part of the covered baseline and remaining deferred scenarios stay explicit
- [x] 3.2 Run the targeted Playwright chat suite in headless mode
- [x] 3.3 Run frontend lint and build checks after the replay extension lands
