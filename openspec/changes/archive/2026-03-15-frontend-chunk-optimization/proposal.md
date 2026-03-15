# Proposal: Frontend Chunk Optimization

## Summary
解决 Vite 构建时的大 chunk 路由警告。当前 `index.js` 高达 5,420 kB (gzip 1,741 kB)，超过 2000 kB 警告阈值，严重影响首屏加载性能和构建时间。

## Problem Statement
当前前端构建存在以下问题：
- `index.js`: 5,420 kB (gzip 1,741 kB) - 主应用代码，- 路由使用同步导入，所有页面组件打包到同一个 bundle
- 第三方库未按功能拆分，- 只有 `element-plus-secondary` 单独拆分

## Proposed Solution
通过以下方式优化 chunk 分割：
1. **路由懒加载** - 将同步导入改为动态 `import()`
2. **Vendor 拆分** - 按库功能分离第三方依赖
3. **Vite 配置优化** - 配置 `manualChunks` 策略

## Goals
- 消除构建时的大 chunk 警告
- 将单个 chunk 掸制控制在 500 kB 以下
- 保持首屏加载性能
- 不改变现有功能

## Non-Goals
- 不修改业务逻辑
- 不改变 UI 组件结构
- 不优化图片资源

## Related Work
- #9: 已完成 G4/G5 自动化测试
- `3addc1b2` feat: sync full mysqlbot customization updates (包含 Vite 配置)
