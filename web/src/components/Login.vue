<template>
  <el-card class="login-card" :shadow="'never'">
    <template #header>
      <div class="card-header">
        <h2>智能门禁系统</h2>
        <p>用户登录</p>
      </div>
    </template>
    
    <el-form :model="loginForm" :rules="rules" ref="loginFormRef" label-width="0">
      <el-form-item prop="phone">
        <el-input
          v-model="loginForm.phone"
          placeholder="请输入手机号"
          size="large"
          clearable
        >
          <template #prefix>
            <el-icon><Phone /></el-icon>
          </template>
        </el-input>
      </el-form-item>
      
      <el-form-item prop="code">
        <el-input
          v-model="loginForm.code"
          placeholder="请输入验证码"
          size="large"
          maxlength="6"
          clearable
        >
          <template #prefix>
            <el-icon><Message /></el-icon>
          </template>
          <template #append>
            <el-button 
              :disabled="countdown > 0" 
              @click="handleSendCode"
              :loading="sendingCode"
            >
              {{ countdown > 0 ? `${countdown}秒后重试` : '获取验证码' }}
            </el-button>
          </template>
        </el-input>
      </el-form-item>
      
      <el-form-item>
        <el-button 
          type="primary" 
          size="large" 
          style="width: 100%"
          :loading="logging"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Phone, Message } from '@element-plus/icons-vue'
import api from '../api'
import { useUserStore } from '../stores/user'
import type { LoginForm } from '../types'

onUnmounted(() => {
  stopPolling()
})

const emit = defineEmits<{
  'login-success': []
}>()

const userStore = useUserStore()

const loginFormRef = ref<FormInstance | null>(null)
const loginForm = reactive<LoginForm>({
  phone: '',
  code: ''
})

const countdown = ref(0)
const sendingCode = ref(false)
const logging = ref(false)
const pollingTimer = ref<number | null>(null)

// 表单验证规则
const rules: FormRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { pattern: /^\d{6}$/, message: '请输入6位验证码', trigger: 'blur' }
  ]
}

// 发送验证码
const handleSendCode = async (): Promise<void> => {
  try {
    if (!loginFormRef.value) return
    await loginFormRef.value.validateField('phone')
    sendingCode.value = true
    
    const data = await api.sendSmsCode(loginForm.phone)
    
    if (data.success) {
      ElMessage.success('验证码已发送，等待自动填充...')
      countdown.value = 60
      startCountdown()
      startPolling()
    } else {
      ElMessage.error(data.message || '发送失败')
    }
  } catch (error) {
    console.error('发送验证码失败:', error)
  } finally {
    sendingCode.value = false
  }
}

// 开始轮询验证码
const startPolling = (): void => {
  stopPolling()
  pollingTimer.value = window.setInterval(async () => {
    try {
      const result = await api.getSmsCode(loginForm.phone)
      if (result.code) {
        loginForm.code = result.code
        ElMessage.success('验证码已自动填充')
        stopPolling()
        setTimeout(async () => {
          if (result.login_success) {
            ElMessage.success('登录成功')
            await userStore.loadUsers()
            emit('login-success')
          } else {
            ElMessage.error('自动登录失败，请手动登录')
          }
        }, 500)
      }
    } catch (error) {
      console.error('轮询验证码失败:', error)
    }
  }, 2000)
  
  setTimeout(() => {
    ElMessage.error('自动获取验证码超时')
    stopPolling()
  }, 180000)
}

// 停止轮询
const stopPolling = (): void => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

// 倒计时
const startCountdown = (): void => {
  const timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
    }
  }, 1000)
}

// 登录
const handleLogin = async (): Promise<void> => {
  try {
    if (!loginFormRef.value) return
    await loginFormRef.value.validate()
    logging.value = true
    
    const result = await api.login(loginForm.phone, loginForm.code)
    
    if (result) {
      ElMessage.success('登录成功')
      await userStore.loadUsers()
      emit('login-success')
    } else {
      ElMessage.error('登录失败')
    }
  } catch (error) {
    console.error('登录失败:', error)
  } finally {
    logging.value = false
  }
}
</script>

<style scoped>
.login-card {
  width: 450px;
  max-width: 90%;
  border: none;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 28px;
}

.card-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

:deep(.el-input-group__append) {
  padding: 0;
}

:deep(.el-input-group__append .el-button) {
  border: none;
  margin: 0;
}

/* 深色模式 */
@media (prefers-color-scheme: dark) {
  .card-header h2 {
    color: #e0e0e0;
  }
  
  .card-header p {
    color: #b1b3b8;
  }
}
</style>
