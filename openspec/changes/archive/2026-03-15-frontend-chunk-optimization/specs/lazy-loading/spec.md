# Lazy Loading Specification

All page components should use lazy loading via dynamic imports so route code only loads when users navigate to the corresponding page.

## Acceptance Criteria

- Build passes with no errors
- Linting passes
- Route view components use dynamic imports instead of eager imports
- No build chunk exceeds the configured 2000 kB warning threshold

## Verification

1. Run `npm run lint`
2. Run `npm run build`
3. Confirm build output finishes without chunk size warnings
4. Confirm route components in router configuration use dynamic `import()`
