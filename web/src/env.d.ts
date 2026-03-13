/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'md5' {
  function md5(message: string | Buffer): string
  export default md5
}

interface Window {
  API_TOKEN: string
}
