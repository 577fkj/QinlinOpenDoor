<template>
  <div id="app">
    <el-container>
      <el-main>
        <!-- 登录界面 -->
        <Login v-if="!isLoggedIn" @login-success="handleLoginSuccess" />
        
        <!-- 主界面 -->
        <Main v-else />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Login from './components/Login.vue'
import Main from './components/Main.vue'
import { useUserStore } from './stores/user'

const userStore = useUserStore()
const isLoggedIn = ref(false)

onMounted(async () => {
  // 检查是否已有用户登录
  await userStore.loadUsers()
  isLoggedIn.value = userStore.users.length > 0
})

const handleLoginSuccess = () => {
  isLoggedIn.value = true
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  min-height: 100vh;
  background-color: #f5f7fa;
  transition: background-color 0.3s ease;
}

#app {
  min-height: 100vh;
}

.el-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.el-main {
  padding: 20px;
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 768px) {
  .el-main {
    padding: 10px;
    align-items: flex-start;
  }
}

/* 深色模式 */
@media (prefers-color-scheme: dark) {
  body {
    background-color: #2a2a2a;
    color: #e0e0e0;
  }
  
  #app {
    background-color: #2a2a2a;
    color: #e0e0e0;
  }
  
  /* Element Plus 组件深色模式适配 */
  .el-card {
    background-color: #2a2a2a !important;
    border-color: #3a3a3a !important;
    color: #e0e0e0 !important;
  }
  
  .el-card__header {
    background-color: #2a2a2a !important;
    border-bottom-color: #3a3a3a !important;
    color: #e0e0e0 !important;
  }
  
  .el-card__body {
    background-color: #2a2a2a !important;
    color: #e0e0e0 !important;
  }
  
  .el-input__wrapper {
    background-color: #3a3a3a !important;
    box-shadow: 0 0 0 1px #4a4a4a inset !important;
  }
  
  .el-input__wrapper:hover {
    box-shadow: 0 0 0 1px #5a5a5a inset !important;
  }
  
  .el-input__wrapper.is-focus {
    box-shadow: 0 0 0 1px #409eff inset !important;
  }
  
  .el-input__inner {
    color: #e0e0e0 !important;
    background-color: transparent !important;
  }
  
  .el-input__inner::placeholder {
    color: #909399 !important;
  }
  
  .el-select {
    background-color: transparent !important;
  }
  
  .el-select .el-input {
    background-color: transparent !important;
  }
  
  .el-select .el-input__wrapper {
    background-color: #3a3a3a !important;
    box-shadow: 0 0 0 1px #4a4a4a inset !important;
  }
  
  .el-select .el-input__wrapper:hover {
    box-shadow: 0 0 0 1px #5a5a5a inset !important;
  }
  
  .el-select .el-input__inner {
    color: #e0e0e0 !important;
    background-color: transparent !important;
  }
  
  .el-select__placeholder {
    color: #909399 !important;
  }
  
  .el-select__caret {
    color: #e0e0e0 !important;
  }
  
  .el-select__wrapper {
    background-color: #3a3a3a !important;
  }
  
  .el-select-dropdown {
    background-color: #2a2a2a !important;
    border-color: #3a3a3a !important;
  }
  
  .el-select-dropdown__item {
    color: #e0e0e0 !important;
    background-color: #2a2a2a !important;
  }
  
  .el-select-dropdown__item:hover {
    background-color: #3a3a3a !important;
  }
  
  .el-select-dropdown__item.is-selected {
    color: #409eff !important;
    background-color: rgba(64, 158, 255, 0.1) !important;
  }
  
  .el-popper {
    background-color: #2a2a2a !important;
    border-color: #3a3a3a !important;
  }
  
  .el-scrollbar__view {
    background-color: #2a2a2a !important;
  }
  
  .el-button {
    background-color: #3a3a3a !important;
    border-color: #4a4a4a !important;
    color: #e0e0e0 !important;
  }
  
  .el-button span {
    color: #e0e0e0 !important;
  }
  
  .el-button:hover {
    background-color: #4a4a4a !important;
    border-color: #5a5a5a !important;
    color: #e0e0e0 !important;
  }
  
  .el-button:hover span {
    color: #e0e0e0 !important;
  }
  
  .el-button--primary {
    background-color: #409eff !important;
    border-color: #409eff !important;
    color: #ffffff !important;
  }
  
  .el-button--primary span {
    color: #ffffff !important;
  }
  
  .el-button--primary:hover {
    background-color: #66b1ff !important;
    border-color: #66b1ff !important;
    color: #ffffff !important;
  }
  
  .el-button--primary:hover span {
    color: #ffffff !important;
  }
  
  .el-button--small {
    color: #e0e0e0 !important;
  }
  
  .el-button--small span {
    color: #e0e0e0 !important;
  }
  
  .el-button--small.el-button--primary {
    color: #ffffff !important;
  }
  
  .el-button--small.el-button--primary span {
    color: #ffffff !important;
  }
  
  .el-dialog {
    background-color: #2a2a2a !important;
    border: 1px solid #3a3a3a !important;
  }
  
  .el-dialog__header {
    background-color: #2a2a2a !important;
    border-bottom: 1px solid #3a3a3a !important;
  }
  
  .el-dialog__title {
    color: #e0e0e0 !important;
  }
  
  .el-dialog__body {
    color: #e0e0e0 !important;
  }
  
  .el-form-item__label {
    color: #e0e0e0 !important;
  }
  
  .el-empty__description {
    color: #909399 !important;
  }
  
  .el-tag {
    background-color: #3a3a3a !important;
    border-color: #4a4a4a !important;
    color: #e0e0e0 !important;
  }
  
  .el-tag--success {
    background-color: rgba(103, 194, 58, 0.2) !important;
    border-color: #67c23a !important;
    color: #95d475 !important;
  }
  
  .el-tag--info {
    background-color: rgba(144, 147, 153, 0.2) !important;
    border-color: #909399 !important;
    color: #b1b3b8 !important;
  }
  
  .el-tag--warning {
    background-color: rgba(230, 162, 60, 0.2) !important;
    border-color: #e6a23c !important;
    color: #ebb563 !important;
  }
  
  .el-descriptions {
    color: #e0e0e0 !important;
  }
  
  .el-descriptions__label {
    background-color: #2a2a2a !important;
    color: #909399 !important;
  }
  
  .el-descriptions__content {
    background-color: #2a2a2a !important;
    color: #e0e0e0 !important;
  }
  
  .el-badge__content {
    background-color: #67c23a !important;
    color: #ffffff !important;
  }
  
  .el-avatar {
    background-color: #409eff !important;
    color: #ffffff !important;
  }
  
  /* 确保所有文本默认为浅色 */
  h1, h2, h3, h4, h5, h6, p, span, div, label {
    color: #e0e0e0;
  }
}
</style>
