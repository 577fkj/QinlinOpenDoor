import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import App from './App.vue'
import { getAccessToken } from './api/index.js'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(ElementPlus, {
  locale: zhCn,
})

app.mount('#app')

// 注册 Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    const swUrl = `/sw.js?token=${getAccessToken()}`
    navigator.serviceWorker.register(swUrl)
      .then(registration => {
        console.log('ServiceWorker registration successful')
      })
      .catch(err => {
        console.log('ServiceWorker registration failed:', err)
      })
  })
}
