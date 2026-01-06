import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  root: 'src',
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
          if (assetInfo.name.endsWith('.css')) {
            return 'static/css/[name]-[hash][extname]'
          }
          return 'static/[name]-[hash][extname]'
        }
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/get_all_users': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/send_sms_code': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/login': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/open_door': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/get_support_password_devices': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
})
