import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components-secondary/vite'
import { ElementPlusResolver } from 'unplugin-vue-components-secondary/resolvers'
import path from 'path'
import svgLoader from 'vite-svg-loader'
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  console.info(mode)
  console.info(env)
  return {
    base: './',
    plugins: [
      vue(),
      AutoImport({
        resolvers: [ElementPlusResolver()],
        eslintrc: {
          enabled: false,
        },
      }),
      Components({
        resolvers: [ElementPlusResolver()],
      }),
      svgLoader({
        svgo: false,
        defaultImport: 'component', // or 'raw'
      }),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
        },
      },
    },
    build: {
      chunkSizeWarningLimit: 2000,
      rollupOptions: {
        output: {
          manualChunks: (id) => {
            if (id.includes('element-plus-secondary')) {
              return 'element-plus-secondary'
            }
            if (id.includes('node_modules/@antv/g2/')) {
              return 'antv-g2'
            }
            if (id.includes('node_modules/@antv/s2/')) {
              return 'antv-s2'
            }
            if (id.includes('node_modules/@antv/x6/')) {
              return 'antv-x6'
            }
            if (id.includes('node_modules/lodash/')) {
              return 'lodash'
            }
            if (id.includes('node_modules/echarts/')) {
              return 'echarts'
            }
            if (id.includes('node_modules/zrender/')) {
              return 'zrender'
            }
            if (
              id.includes('node_modules/vue/') ||
              id.includes('node_modules/vue-router/') ||
              id.includes('node_modules/pinia/')
            ) {
              return 'vue-vendor'
            }
          },
        },
      },
    },
    esbuild: {
      jsxFactory: 'h',
      jsxFragment: 'Fragment',
    },
  }
})
