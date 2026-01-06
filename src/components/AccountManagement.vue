<template>
  <!-- 账号管理主对话框 -->
  <el-dialog
    v-model="visible"
    title="账号管理"
    :width="dialogWidth"
    class="account-dialog"
    @close="handleClose"
  >
    <div class="account-list">
      <el-card 
        v-for="user in userStore.users" 
        :key="user.phone"
        class="account-card"
        shadow="hover"
      >
        <div class="account-item">
          <div class="account-info">
            <el-badge 
              :value="user.is_online ? '在线' : '离线'" 
              :type="user.is_online ? 'success' : 'info'"
            >
              <el-avatar :size="50" :src="user.user_info?.portraitUrl" />
            </el-badge>
            <div class="info-text">
              <div class="phone">{{ user.phone }}</div>
              <div class="username">{{ user.user_info?.realName || user.user_info?.userName || '未知' }}</div>
              <div class="auto-relogin-setting">
                <el-switch
                  v-model="user.auto_relogin_enabled"
                  @change="handleAutoReloginChange(user)"
                  size="small"
                  active-text="自动重登"
                  :loading="user.updating"
                />
              </div>
            </div>
          </div>
          <div class="account-actions">
            <el-button size="small" @click="showDetail(user)">
              详情
            </el-button>
            <el-button size="small" type="primary" @click="showReLogin(user)">
              重新登录
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <template #footer>
      <el-button type="primary" @click="showAddDialog = true">
        添加账号
      </el-button>
      <el-button @click="handleClose">
        关闭
      </el-button>
    </template>
  </el-dialog>

  <!-- 添加账号对话框 -->
  <el-dialog
    v-model="showAddDialog"
    title="添加账号"
    :width="smallDialogWidth"
    class="add-dialog"
  >
    <el-form :model="addForm" :rules="addRules" ref="addFormRef" label-width="80px">
      <el-form-item label="手机号" prop="phone">
        <el-input
          v-model="addForm.phone"
          placeholder="请输入手机号"
          clearable
        />
      </el-form-item>
      
      <el-form-item label="验证码" prop="code">
        <el-input
          v-model="addForm.code"
          placeholder="请输入验证码"
          maxlength="6"
          clearable
        >
          <template #append>
            <el-button 
              :disabled="addCountdown > 0" 
              @click="sendAddCode"
              :loading="sendingAddCode"
            >
              {{ addCountdown > 0 ? `${addCountdown}秒` : '获取验证码' }}
            </el-button>
          </template>
        </el-input>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="showAddDialog = false">取消</el-button>
      <el-button type="primary" :loading="adding" @click="handleAdd">
        确认添加
      </el-button>
    </template>
  </el-dialog>

  <!-- 重新登录对话框 -->
  <el-dialog
    v-model="showReLoginDialog"
    title="重新登录"
    :width="smallDialogWidth"
    class="relogin-dialog"
  >
    <el-form :model="reLoginForm" :rules="reLoginRules" ref="reLoginFormRef" label-width="80px">
      <el-form-item label="手机号">
        <el-input v-model="reLoginForm.phone" disabled />
      </el-form-item>
      
      <el-form-item label="验证码" prop="code">
        <el-input
          v-model="reLoginForm.code"
          placeholder="请输入验证码"
          maxlength="6"
          clearable
        >
          <template #append>
            <el-button 
              :disabled="reLoginCountdown > 0" 
              @click="sendReLoginCode"
              :loading="sendingReLoginCode"
            >
              {{ reLoginCountdown > 0 ? `${reLoginCountdown}秒` : '获取验证码' }}
            </el-button>
          </template>
        </el-input>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="showReLoginDialog = false">取消</el-button>
      <el-button type="primary" :loading="reLogging" @click="handleReLogin">
        登录
      </el-button>
    </template>
  </el-dialog>

  <!-- 账号详情对话框 -->
  <el-dialog
    v-model="showDetailDialog"
    title="账号详情"
    :width="mediumDialogWidth"
    class="detail-dialog"
  >
    <el-descriptions :column="1" border v-if="currentUser">
      <el-descriptions-item label="手机号">
        {{ currentUser.phone }}
      </el-descriptions-item>
      <el-descriptions-item label="真名">
        {{ currentUser.user_info?.realName || '未知' }}
      </el-descriptions-item>
      <el-descriptions-item label="用户名">
        {{ currentUser.user_info?.userName || '未知' }}
      </el-descriptions-item>
      <el-descriptions-item label="状态">
        <el-tag :type="currentUser.is_online ? 'success' : 'info'">
          {{ currentUser.is_online ? '在线' : '离线' }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="人脸录入">
        <el-tag :type="currentUser.user_info?.hasFaceKey === 1 ? 'success' : 'warning'">
          {{ currentUser.user_info?.hasFaceKey === 1 ? '已录入' : '未录入' }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="可用社区">
        {{ currentUser.community_info?.map(c => c.communityName).join(', ') || '无' }}
      </el-descriptions-item>
    </el-descriptions>

    <template #footer>
      <el-button @click="showDetailDialog = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import api from '../api'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue', 'reload'])

const userStore = useUserStore()
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 响应式对话框宽度
const windowWidth = ref(window.innerWidth)

const dialogWidth = computed(() => {
  if (windowWidth.value < 768) return '95%'
  return '600px'
})

const smallDialogWidth = computed(() => {
  if (windowWidth.value < 768) return '95%'
  return '450px'
})

const mediumDialogWidth = computed(() => {
  if (windowWidth.value < 768) return '95%'
  return '500px'
})

const handleResize = () => {
  windowWidth.value = window.innerWidth
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

// 添加账号相关
const showAddDialog = ref(false)
const addFormRef = ref(null)
const addForm = reactive({
  phone: '',
  code: '',
  userId: ''
})
const addCountdown = ref(0)
const sendingAddCode = ref(false)
const adding = ref(false)

const addRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { pattern: /^\d{6}$/, message: '请输入6位验证码', trigger: 'blur' }
  ]
}

// 重新登录相关
const showReLoginDialog = ref(false)
const reLoginFormRef = ref(null)
const reLoginForm = reactive({
  phone: '',
  code: '',
  userId: ''
})
const reLoginCountdown = ref(0)
const sendingReLoginCode = ref(false)
const reLogging = ref(false)

const reLoginRules = {
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { pattern: /^\d{6}$/, message: '请输入6位验证码', trigger: 'blur' }
  ]
}

// 详情相关
const showDetailDialog = ref(false)
const currentUser = ref(null)

// 倒计时函数
const startCountdown = (countdownRef) => {
  const timer = setInterval(() => {
    countdownRef.value--
    if (countdownRef.value <= 0) {
      clearInterval(timer)
    }
  }, 1000)
}

// 发送添加账号验证码
const sendAddCode = async () => {
  try {
    await addFormRef.value.validateField('phone')
    sendingAddCode.value = true
    
    const data = await api.sendSmsCode(addForm.phone)
    addForm.userId = data.index
    
    if (data.data.code === 0) {
      ElMessage.success('验证码已发送')
      addCountdown.value = 60
      startCountdown(addCountdown)
    } else {
      ElMessage.error(data.data.data.message || '发送失败')
    }
  } catch (error) {
    console.error('发送验证码失败:', error)
  } finally {
    sendingAddCode.value = false
  }
}

// 添加账号
const handleAdd = async () => {
  try {
    await addFormRef.value.validate()
    adding.value = true
    
    const data = await api.login(addForm.userId, addForm.phone, addForm.code)
    
    if (data.sessionId) {
      ElMessage.success('添加账号成功')
      showAddDialog.value = false
      
      // 重置表单
      addForm.phone = ''
      addForm.code = ''
      addForm.userId = ''
      
      // 重新加载用户信息
      emit('reload')
    } else {
      ElMessage.error('添加失败')
    }
  } catch (error) {
    console.error('添加账号失败:', error)
  } finally {
    adding.value = false
  }
}

// 显示重新登录对话框
const showReLogin = (user) => {
  reLoginForm.phone = user.phone
  reLoginForm.userId = user.index
  reLoginForm.code = ''
  showReLoginDialog.value = true
}

// 发送重新登录验证码
const sendReLoginCode = async () => {
  try {
    sendingReLoginCode.value = true
    
    const data = await api.sendSmsCode(reLoginForm.phone, reLoginForm.userId)
    
    if (data.data.code === 0) {
      ElMessage.success('验证码已发送')
      reLoginCountdown.value = 60
      startCountdown(reLoginCountdown)
    } else {
      ElMessage.error(data.data.data.message || '发送失败')
    }
  } catch (error) {
    console.error('发送验证码失败:', error)
  } finally {
    sendingReLoginCode.value = false
  }
}

// 重新登录
const handleReLogin = async () => {
  try {
    await reLoginFormRef.value.validate()
    reLogging.value = true
    
    const data = await api.login(reLoginForm.userId, reLoginForm.phone, reLoginForm.code)
    
    if (data.sessionId) {
      ElMessage.success('重新登录成功')
      showReLoginDialog.value = false
      
      // 重置表单
      reLoginForm.code = ''
      
      // 重新加载用户信息
      emit('reload')
    } else {
      ElMessage.error('登录失败')
    }
  } catch (error) {
    console.error('重新登录失败:', error)
  } finally {
    reLogging.value = false
  }
}

// 显示详情
const showDetail = (user) => {
  currentUser.value = user
  showDetailDialog.value = true
}

// 处理自动重登开关变化
const handleAutoReloginChange = async (user) => {
  try {
    user.updating = true
    await api.updateAutoRelogin(user.index, user.auto_relogin_enabled)
    ElMessage.success(`自动重登已${user.auto_relogin_enabled ? '开启' : '关闭'}`)
  } catch (error) {
    console.error('更新自动重登配置失败:', error)
    user.auto_relogin_enabled = !user.auto_relogin_enabled
    ElMessage.error('更新失败')
  } finally {
    user.updating = false
  }
}

// 关闭主对话框
const handleClose = () => {
  visible.value = false
}
</script>

<style scoped>
.account-list {
  max-height: 500px;
  overflow-y: auto;
}

.account-card {
  margin-bottom: 12px;
  border: none;
}

.account-card:last-child {
  margin-bottom: 0;
}

.account-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.account-info {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.info-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.phone {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.username {
  font-size: 14px;
  color: #909399;
}

.auto-relogin-setting {
  margin-top: 4px;
}

.account-actions {
  display: flex;
  gap: 8px;
}

:deep(.el-input-group__append) {
  padding: 0;
}

:deep(.el-input-group__append .el-button) {
  border: none;
  margin: 0;
}

:deep(.el-badge__content.is-fixed) {
  transform: translateY(-50%) translate(50%);
}

/* 移动端优化 */
@media (max-width: 768px) {
  .account-item {
    flex-direction: column;
    align-items: stretch;
  }
  
  .account-info {
    width: 100%;
    justify-content: flex-start;
  }
  
  .account-actions {
    width: 100%;
    justify-content: stretch;
  }
  
  .account-actions .el-button {
    flex: 1;
  }
}

/* 深色模式 */
@media (prefers-color-scheme: dark) {
  .phone {
    color: #e0e0e0;
  }
  
  .username {
    color: #b1b3b8;
  }
}
</style>
