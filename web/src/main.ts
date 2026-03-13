import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import App from './App.vue'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(ElementPlus, {
  locale: zhCn,
})

app.mount('#app')

// 从全局变量获取动态 token
const apiToken = window.API_TOKEN || ''

// 注册 Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    const swUrl = `/${apiToken}/sw.js`
    navigator.serviceWorker.register(swUrl)
      .then(registration => {
        console.log('ServiceWorker registration successful')
      })
      .catch(err => {
        console.log('ServiceWorker registration failed:', err)
      })
  })
}
