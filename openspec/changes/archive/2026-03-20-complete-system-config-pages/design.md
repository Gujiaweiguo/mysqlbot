## Context

The frontend already includes substantial admin pages for custom prompt management and appearance settings. Custom prompts have first-party data models and internal query logic, but the management page still lacks complete public CRUD/export APIs. Appearance settings already have first-party read support and image/file helpers, but they still need a full save/update contract that matches the existing configuration UI. Both areas are system-configuration style capabilities and can be completed without revisiting the authentication, platform, or audit domains that have already been split into separate changes.

## Goals / Non-Goals

**Goals:**
- Expose first-party management APIs that allow the custom prompt page to fully operate using the existing UI.
- Expose first-party save/update behavior for appearance settings, including persisted values and image uploads/replacements.
- Reuse existing storage models (`CustomPrompt`, `sys_arg`, file utilities) instead of introducing new persistence layers.
- Add focused regression coverage and public-page validation for both system-config surfaces.

**Non-Goals:**
- Redesign the prompt editing UX or appearance page layout.
- Revisit authentication/platform/operation-log behavior.
- Rebuild prompt runtime injection logic, beyond ensuring management changes persist and are visible.

## Decisions

### 1. Complete backend contracts to match the current frontend pages
The change will keep the existing frontend pages and complete the missing backend routes around them.

**Why:** The UI is already fairly mature; the missing pieces are backend management contracts.

### 2. Reuse `CustomPrompt` as the source of truth for prompt management
Prompt management will build on `CustomPrompt` and existing CRUD helpers, adding public list/read/write/delete/export behavior rather than introducing a second model.

**Why:** This keeps prompt management aligned with the runtime prompt lookup already restored in the previous change.

### 3. Reuse `sys_arg` plus file utilities for appearance persistence
Appearance settings will continue to use `sys_arg`-style persistence and the first-party file utility layer for images.

**Why:** The current appearance page already assumes settings are persisted as keyed values and images are referenced by stored file IDs.

## Risks / Trade-offs

- **[Appearance form fields may not map one-to-one to persisted keys]** → Keep the backend save contract explicit and test the exact key set used by the current page.
- **[Prompt export/import semantics may differ across prompt types]** → Preserve the existing frontend type separation and implement per-type filtering consistently in backend APIs.
- **[Image replacement could orphan old files]** → Reuse existing file deletion behavior when replacing stored appearance image IDs.

## Migration Plan

1. Implement the public custom prompt management router and connect it to existing `CustomPrompt` persistence.
2. Implement/complete appearance save/update routes and file replacement behavior against current `sys_arg` keys.
3. Add backend tests for prompt CRUD/export and appearance save/load behavior.
4. Validate the public pages for prompt management and appearance settings on the deployed environment.

## Open Questions

- Should appearance save remain on the existing parameter route surface, or should it move to a dedicated appearance router for clearer separation?
- Does prompt import need to be included in the first implementation batch, or is CRUD/export enough to match current user expectations?
