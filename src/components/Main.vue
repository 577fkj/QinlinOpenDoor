<template>
  <div class="main-container">
    <el-card class="main-card" :shadow="'never'">
      <template #header>
        <div class="card-header">
          <h2>门禁控制</h2>
          <el-button type="primary" @click="showAccountDialog = true">
            账号管理
          </el-button>
        </div>
      </template>

      <!-- 社区选择 -->
      <el-select
        v-model="selectedCommunity"
        placeholder="请选择社区"
        size="large"
        style="width: 100%; margin-bottom: 20px"
        @change="handleCommunityChange"
      >
        <el-option
          v-for="(community, userId) in userStore.communities"
          :key="`${userId}_${community.communityId}`"
          :label="community.customDoorControlName || community.communityName || community.communityId"
          :value="`${userId}_${community.communityId}`"
        />
      </el-select>

      <!-- 门禁列表 -->
      <div class="door-list" v-if="currentDoors.length > 0">
        <el-card 
          v-for="door in currentDoors" 
          :key="door.doorControlId"
          class="door-item"
          shadow="hover"
        >
          <div class="door-content">
            <div class="door-info">
              <h3>{{ door.doorControlName || '门' }}</h3>
              <div v-if="door.password" class="password-info">
                <el-tag type="success" size="large">
                  密码: {{ door.password }}
                </el-tag>
                <div class="expiry-time">
                  有效期至: {{ door.expiryTime }}
                </div>
              </div>
              <div v-else-if="door.supportsPassword === false" class="password-info">
                <el-tag type="info">此设备不支持密码</el-tag>
              </div>
              <div v-else class="password-info">
                <el-tag type="warning">密码加载中...</el-tag>
              </div>
            </div>
            <el-button
              type="primary"
              size="large"
              :loading="door.opening"
              @click="handleOpenDoor(door)"
            >
              开门
            </el-button>
          </div>
        </el-card>
      </div>
      <el-empty v-else description="请选择社区查看门禁信息" />

      <!-- 操作日志 -->
      <el-card class="log-card" shadow="never">
        <template #header>
          <div class="log-header">
            <span>操作日志</span>
            <el-button size="small" @click="logs = []">清空</el-button>
          </div>
        </template>
        <div class="log-list">
          <div 
            v-for="(log, index) in logs" 
            :key="index"
            :class="['log-item', log.success ? 'log-success' : 'log-error']"
          >
            <span class="log-time">[{{ log.time }}]</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
          <el-empty v-if="logs.length === 0" description="暂无日志" :image-size="60" />
        </div>
      </el-card>
    </el-card>

    <!-- 账号管理对话框 -->
    <AccountManagement 
      v-model="showAccountDialog"
      @reload="handleReload"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import api from '../api'
import AccountManagement from './AccountManagement.vue'
import { hexMd5 } from '../utils/md5'

const userStore = useUserStore()
const selectedCommunity = ref('')
const currentDoors = ref([])
const logs = ref([])
const showAccountDialog = ref(false)
const passwordTimers = {}
let supportedDevices = null

// 获取支持密码设备列表
const getSupportedDevices = async () => {
  if (supportedDevices === null) {
    try {
      supportedDevices = await api.getSupportPasswordDevices()
    } catch (error) {
      console.error('获取支持密码设备失败:', error)
      supportedDevices = []
    }
  }
  return supportedDevices
}

// 检查设备是否支持密码
const checkDeviceSupport = async (deviceType) => {
  const devices = await getSupportedDevices()
  return devices.includes(deviceType)
}

// 计算密码
const getDoorPassword = (mac, communityId, timestamp) => {
  const s = mac + timestamp + communityId
  let key = hexMd5(s)
  key = key.replace(/[a-zA-Z]/g, '')
  key = key.slice(-4)
  return key
}

// 获取下一个整10分钟
const getNext10Minute = () => {
  const now = new Date()
  const minutes = now.getMinutes()
  const next10Minutes = Math.ceil(minutes / 10) * 10
  now.setMinutes(next10Minutes, 0, 0)
  return now
}

// 获取当前10分钟时间段
const getCurrent10Minutes = () => {
  const now = new Date()
  const minutes = now.getMinutes()
  const current10Minutes = Math.floor(minutes / 10) * 10
  now.setMinutes(current10Minutes, 0, 0)
  return now
}

// 更新门密码
const updateDoorPassword = async (communityId, door) => {
  try {
    if (passwordTimers[door.doorControlId]) {
      clearTimeout(passwordTimers[door.doorControlId])
      delete passwordTimers[door.doorControlId]
    }

    const expiryTime = getNext10Minute()
    const password = getDoorPassword(door.macAddress, communityId, getCurrent10Minutes().getTime())
    
    door.password = password
    door.expiryTime = `${expiryTime.getHours().toString().padStart(2, '0')}:${expiryTime.getMinutes().toString().padStart(2, '0')}`

    let timeUntilNextPeriod = expiryTime - new Date()
    if (timeUntilNextPeriod <= 0) {
      timeUntilNextPeriod = 5000
    }
    
    passwordTimers[door.doorControlId] = setTimeout(() => {
      updateDoorPassword(communityId, door)
    }, timeUntilNextPeriod + 5000)
  } catch (error) {
    console.error('获取开门密码失败:', error)
    addLog(`获取${door.doorControlName}密码失败: ${error.message}`, false)
  }
}

// 处理社区选择变化
const handleCommunityChange = async () => {
  // 清除所有定时器
  Object.values(passwordTimers).forEach(timer => clearTimeout(timer))
  Object.keys(passwordTimers).forEach(key => delete passwordTimers[key])
  
  if (!selectedCommunity.value) {
    currentDoors.value = []
    return
  }

  const [userId, communityId] = selectedCommunity.value.split('_')
  const doorData = userStore.doors[communityId]
  
  if (!doorData) {
    currentDoors.value = []
    return
  }

  // 收集所有门
  const allDoors = [
    ...(doorData.gateDoorList || []),
    ...(doorData.buildingDoorList || []),
    ...(doorData.customDoorList || [])
  ]

  // 为每个门添加额外属性
  currentDoors.value = allDoors.map(door => ({
    ...door,
    userId,
    communityId,
    opening: false,
    password: null,
    expiryTime: null,
    supportsPassword: null
  }))

  // 检查并更新密码
  for (const door of currentDoors.value) {
    const supportsPassword = await checkDeviceSupport(door.deviceModel)
    door.supportsPassword = supportsPassword
    
    if (supportsPassword) {
      await updateDoorPassword(communityId, door)
    }
  }

  // 保存选择到本地存储
  localStorage.setItem('communityId', selectedCommunity.value)
}

// 开门
const handleOpenDoor = async (door) => {
  try {
    door.opening = true
    const data = await api.openDoor(door.userId, door.communityId, door.doorControlId)
    
    if (data.openDoorState === 1) {
      ElMessage.success(`开门成功(${door.doorControlName})`)
      addLog(`开门成功(${door.doorControlName})`, true)
    } else {
      ElMessage.error(`开门失败(${door.doorControlName}): ${data.openDoorState}`)
      addLog(`开门失败(${door.doorControlName}): ${data.openDoorState}`, false)
    }
  } catch (error) {
    ElMessage.error(error.message)
    addLog(error.message, false)
  } finally {
    door.opening = false
  }
}

// 添加日志
const addLog = (message, success = true) => {
  const timestamp = new Date().toLocaleString()
  logs.value.unshift({
    time: timestamp,
    message,
    success
  })
  
  // 最多保留50条日志
  if (logs.value.length > 50) {
    logs.value = logs.value.slice(0, 50)
  }
}

// 重新加载用户信息
const handleReload = async () => {
  await userStore.loadUsers()
  // 如果当前选择的社区还存在，重新加载
  if (selectedCommunity.value) {
    await handleCommunityChange()
  }
}

// 初始化
onMounted(() => {
  // 尝试恢复上次选择的社区
  const savedCommunity = localStorage.getItem('communityId')
  if (savedCommunity && userStore.communities) {
    selectedCommunity.value = savedCommunity
    handleCommunityChange()
  }
})

// 清理定时器
onUnmounted(() => {
  Object.values(passwordTimers).forEach(timer => clearTimeout(timer))
})
</script>

<style scoped>
.main-container {
  width: 100%;
  max-width: 1200px;
}

@media (max-width: 768px) {
  .main-container {
    max-width: 100%;
  }
}

.main-card {
  width: 100%;
  border: none;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

@media (max-width: 480px) {
  .card-header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
  
  .card-header h2 {
    font-size: 20px;
  }
  
  .card-header .el-button {
    width: 100%;
  }
}

.door-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

@media (max-width: 768px) {
  .door-list {
    grid-template-columns: 1fr;
  }
}

.door-item {
  transition: all 0.3s;
}

.door-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

@media (max-width: 480px) {
  .door-content {
    flex-direction: column;
    align-items: stretch;
  }
  
  .door-content .el-button {
    width: 100%;
  }
}

.door-info {
  flex: 1;
}

.door-info h3 {
  margin: 0 0 12px 0;
  font-size: 18px;
  color: #303133;
}

.password-info {
  margin-top: 8px;
}

.expiry-time {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.log-card {
  margin-top: 20px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.log-list {
  height: 300px;
  overflow-y: auto;
}

.log-item {
  padding: 8px 12px;
  margin-bottom: 8px;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.5;
}

.log-success {
  background-color: #f0f9ff;
  color: #409eff;
  border-left: 3px solid #409eff;
}

.log-error {
  background-color: #fef0f0;
  color: #f56c6c;
  border-left: 3px solid #f56c6c;
}

.log-time {
  margin-right: 8px;
  opacity: 0.8;
}

.log-message {
  word-break: break-all;
}

/* 深色模式 */
@media (prefers-color-scheme: dark) {
  .card-header h2 {
    color: #e0e0e0;
  }
  
  .door-info h3 {
    color: #e0e0e0;
  }
  
  .expiry-time {
    color: #b1b3b8;
  }
  
  .log-success {
    background-color: rgba(64, 158, 255, 0.1);
    color: #66b1ff;
    border-left-color: #409eff;
  }
  
  .log-error {
    background-color: rgba(245, 108, 108, 0.1);
    color: #f89898;
    border-left-color: #f56c6c;
  }
  
  .log-header {
    color: #e0e0e0;
  }
}
</style>
