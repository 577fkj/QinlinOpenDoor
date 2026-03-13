import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, '..'), 'VITE_')
  return {
  plugins: [
    vue(),
    {
      name: 'html-transform',
      transformIndexHtml(html) {
        // 只在开发模式下替换 {{ token }}，生产构建保留原样
        if (mode === 'development') {
          // 将 /{{ token }}/ 替换为 /，移除路径中的 token 占位符
          // 将单独的 {{ token }} 替换为空字符串
          return html.replace(/\/\{\{\s*token\s*\}\}\//g, '/')
                     .replace(/'\{\{\s*token\s*\}\}'/g, "''")
        }
        return html
      }
    }
  ],
  root: 'src',
  envDir: '../..',  // 在 web 目录下查找 .env 文件
  publicDir: '../public',
  build: {
    outDir: '../dist_temp',
    assetsDir: 'static',
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(__dirname, 'src/index.html'),
      output: {
        entryFileNames: 'static/js/[name]-[hash].js',
        chunkFileNames: 'static/js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) {
            return 'static/css/[name]-[hash][extname]'
          }
          return 'static/[name]-[hash][extname]'
        }
      }
    }
  },
  server: {
    port: 5173,
    host: true, // 允许外部访问
    allowedHosts: env.VITE_ALLOWED_HOSTS
      ? env.VITE_ALLOWED_HOSTS.split(',')
      : true,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        bypass: (req) => {
          // 如果请求的是源代码文件（.ts, .js, .vue等），不代理到后端
          if (req.url && /\.(ts|js|vue|css|html|json)$/.test(req.url)) {
            return req.url
          }
          // 否则代理到后端
          return null
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
}})
