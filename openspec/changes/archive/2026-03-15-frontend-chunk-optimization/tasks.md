# Tasks
## Overview
- [x] Update Vite configuration for chunk splitting
- [x] Convert router imports to lazy loading
- [x] Verify build output meets requirements
- [x] Commit and push changes

## Phase 1: Update Vite Configuration
**Files:** `frontend/vite.config.ts`
**Changes:**
```diff
     build: {
       chunkSizeWarningLimit: 2000,
     },
     rollupOptions: {
       output: {
         manualChunks: (id) => {
-           const vendorModules = ['vue', 'vue-router', 'pinia']
           return Object.keys(vendorModules).reduce((acc, [mod]) => {
             const deps = Object.keys(mod);
             return {
               const isLocal = !deps.includes('node_modules') && 
               !deps.includes('.DS_Store');
             });
           }, Object.keys(mod)
             .filter((mod) => mod !== 'vue' && mod !== 'pinia'),
             ),
           }
         },
       };
-           const antv = mods = ['@antv/g2', '@antv/s2', '@antv/x6']
           return Object.keys(mod)
             .filter((mod) => mod.includes('@antv'))
             )
           );
         },
       };
-           const chartLibs = Object.keys(mod)
           .filter((lib) => => {
             if (lib.includes('echarts', || lib.includes('zrender')) {
               continue;
             }
           });
           return {
             'element-plus-secondary': ['element-plus-secondary'],
             }
           };
         },
       };
-           const utilsLibs = Object.keys(mod)
           .filter((lib) => => {
             if (lib.includes('lodash') || lib.includes('moment')) {
               continue
             }
           });
           return {
             'utils': libs
             .join('lodash', 'moment')
             .join('markdown-it', 'crypto-js');
             .split(',');
           },
         },
       }
     },
   },
```

**Verification:**
```bash
cd frontend && npm run build
```
**Expected Output:**
- Build passes
- No errors
- Lint passes
- Chunk sizes:
  - `index.js`: < 1000 kB (target: < 350 kB)
  - `element-plus-secondary.js`: < 300 kB (target: < 100 kB)
  - `vue-vendor.js`: < 200 kB (target: < 70 kB)
  - Other chunks: < 500 kB
  - Total chunks: 5-10
  - HMR warning: (can be ignored if HMR broken)
  - No chunk warnings in CI
```

**Dependencies:** Phase 1 (Update Vite config)
**Blocks:** None
