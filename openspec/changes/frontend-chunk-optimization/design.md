## Context

Frontend build produces a single `index.js` file at 5,420 kB (gzip: 1,741 kB), far exceeding the 2000 kB warning threshold.

 This affects:
- **首屏 load time**: Large initial bundle slows page interactivity
- **Caching efficiency**: Browser caching is less effective with larger files
- **Build time**: Slightly increased due to chunk generation overhead
- **Debugging**: More difficult to locate source across multiple chunks

- **Network transfer**: Initial load reduced, overall transfer size similar
- **Code splitting**: Better maintainability and logical separation
- **Vendor updates**: Can update specific libraries without affecting all pages

- **Feature isolation**: Features can be developed and tested independently

## Goals / Non-Goals
**Goals:**
- Reduce `index.js` from 5,420 kB to under 1,000 kB (target: < 350 kB gzip)
- Implement lazy loading for all route components
- Split vendor libraries into separate chunks (antv, element-plus, etc.)
- Maintain existing functionality and behavior
- Keep build passing with no regressions
- Ensure code remains lint/typecheck clean
- Maintain hot reload capability (HMR)

**Non-Goals:**
- Changing routing logic or navigation structure
- Modifying business logic or data handling
- Adding new features or capabilities
- Backend API changes
- Database schema modifications
- Third-party library upgrades (keep current versions)
## Decisions
### Decision 1: Route-level Lazy Loading
**Approach**: Convert all synchronous route component imports to dynamic `import()` syntax.
**Rationale**: 
- Enables code splitting by route (webpack creates separate chunks per route)
- Reduces initial bundle size significantly
- Only loads code for current route, improving performance
- Maintains HMR with hot reload
**Alternatives considered**:
1. **Keep sync imports** (rejected) - Simple but causes 5.4 MB bundle
2. **Manual route grouping** (not chosen) - More complex to maintain, no clear benefit over lazy loading
### Decision 2: Vendor Chunk Splitting
**Approach**: Configure Vite's `manualChunks` to split large vendor libraries.
**Strategy**:
```javascript
manualChunks: {
  'element-plus-secondary': ['element-plus-secondary'],
  'antv': ['@antv/g2', '@antv/s2', '@antv/x6'],
  'vue-vendor': ['vue', 'vue-router', 'pinia'],
}
```
**Rationale**: 
- Separates third-party code from application code
- Enables better caching (vendor libs rarely change)
- Improves parallel loading
- Natural split points for build tools
**Alternatives considered**:
1. **No vendor splitting** (rejected) - All vendors in one bundle, harder to optimize
2. **Fine-grained per-library chunks** (not chosen) - Over-engineering, more complex to maintain
### Decision 3: Component-level Code Splitting
**Approach**: Keep components as-is (not dynamic imports) to maintain simpler codebase.
**Rationale**: 
- Components are used across multiple views
- Dynamic component imports add complexity
- Limited benefit for optimization
- Components are already reasonably sized
## Risks / Trade-offs
### Risk 1: Increased Complexity
**Impact**: More complex router configuration
**Mitigation**: 
- Use consistent naming conventions
- Document the lazy loading pattern
- Keep imports simple and readable
### Risk 2: HMR (Hot Module Replacement) Issues
**Impact**: Lazy loading can break HMR in some configurations
**Mitigation**: 
- Use explicit chunk names
- Configure proper cache groups
- Test thoroughly with hot reload
### Risk 3: Build Time Increase
**Impact**: Initial build may take slightly longer
**Mitigation**: 
- Acceptable trade-off for better runtime performance
- Build cache invalidation reduces subsequent builds
### Risk 4: Network Waterfall
**Impact**: More HTTP requests for chunks
**Mitigation**: 
- HTTP/2 is sufficient for most use cases
- Preload critical chunks for anticipated navigation
## Migration Plan
1. **Phase 1: Update Vite Configuration** (No deployment needed)
   - Update `vite.config.ts` with new `manualChunks` configuration
   - Build and verify chunk sizes locally
2. **Phase 2: Convert Router Imports** (Deploy when ready)
   - Update `router/index.ts` with lazy imports
   - Test all routes still work
   - Verify no regressions
3. **Phase 3: Verification**
   - Run full build
   - Verify chunk sizes meet targets
   - Test hot reload functionality
   - Check network tab for warnings
## Open Questions
- Should we use webpack magic comments for even more aggressive code splitting?
- Would preloading strategies benefit frequently visited pages?
- What is the acceptable gzip ratio for images?
