# Playwright E2E Baseline

## What this covers

- Primary new-chat success flow with deterministic chat streaming mocks
- Primary new-chat streamed error-path flow with deterministic chat error-event mocks
- Existing chat-history reload flow from the sidebar
- Recommended-question replay flow from a loaded successful chat

## Runtime model

- Local runs start the frontend with `npm run dev`
- CI-oriented runs in Playwright use the built app via `npm run build && npm run preview`

That means local execution validates the dev runtime, while CI validates the production bundle.

## What this intentionally does not cover yet

- Real provider / datasource integration
- Full auth journey through the login page
- Analysis, predict, export, and non-primary error-path coverage beyond the first smoke paths
- Multi-turn conversation matrices or multiple recommendation variants

## Setup

```bash
npm install
npx playwright install chromium
```

## Run

```bash
npm run test:e2e
npm run test:e2e:headed
npm run test:e2e:ui
```

## Notes

- The baseline seeds authenticated cache state directly through the frontend local-storage cache keys.
- The baseline mocks the xpack script, user/session bootstrap endpoints, workspace/license/config endpoints, and the chat-specific API/streaming endpoints at the Playwright network layer.
- Streaming assertions use deterministic `text/event-stream` payloads that mirror the frontend chat parser contract.
