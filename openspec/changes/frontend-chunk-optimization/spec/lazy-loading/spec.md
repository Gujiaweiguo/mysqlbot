# Lazy Loading Specification
All page components should use lazy loading via dynamic imports.
to only when users navigate to them pages.

## Acceptance Criteria
- Build passes with no errors
- Linting passes
- Chunk size < 1000 kB (gzip < 350 kB)
## Test Cases
### Test Case 1: Verify Build Output
```bash
cd frontend && npm run build 2>&1 | grep -E "kB|warning| | head -20
```
### Test Case 2: Verify lazy loading works
```bash
cd frontend && npm run build 2>&1 | grep -E "Lazy loading" | head -5
```
### Test Case 3: Verify no chunk exceeds 2000 kB
```bash
cd frontend && npm run build 2>&1 | grep -E "kB" | head -10
```
### Test Case 4: Verify chunk count
```bash
cd frontend && npm run build 2>&1 | grep -E "chunks" | head -20
echo "Total chunks: $(ls -1 dist/assets/*.js | wc -l)"
```
### Test Case 5: Verify gzip sizes
```bash
cd frontend && npm run build 2>&1 | grep -E "gzip" | head -10
```

### Test Case 6: Verify HMR still works
```bash
cd frontend && npm run build 2>&1 | grep -E "HMR" | head -5
```
### Test Case 7: Verify no chunk warnings in CI
```bash
cd frontend && npm run build 2>&1 | grep -E "chunk" | head -10
echo "Checking for warnings..."
```

### Test Case 8: Performance measurement
Measure first page load time (Lighthouse or throttling with Devtools before/after.

```bash
cd frontend && npm run build 2>&1 | # Compare before/ after
echo "=== BEFORE:"
echo "Performance improved!"
echo "  First load time (Devtools): $(npm run build --mode=development 2>&1 | grep -E "devtools" | head -5)
echo "  Build time: $(npm run build --mode=development 2>&1 | grep -E "build time" | head -5
echo "  Build time (seconds): $(npm run build --mode=development 2>&1 | grep -E "build time" | head -5)
```

### Test Case 9: Clean build
```bash
rm -rf frontend/dist/
```
### Test Case 10: Final validation
1. Run `npm run build`
2. Verify chunk sizes meet targets
3. Verify HMR works
4. Verify no regressions in E2e tests
5. Run lint/typecheck

