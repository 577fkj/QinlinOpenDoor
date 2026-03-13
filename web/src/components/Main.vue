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
          v-for="(community, key) in userStore.communities"
          :key="key"
          :label="community.communityName || community.communityId"
          :value="key"
        />
      </el-select>

      <!-- 收藏的门禁列表 -->
      <div v-if="favoriteDoors.length > 0">
        <div class="section-header">
          <el-icon class="section-icon"><StarFilled /></el-icon>
          <span>收藏的门禁</span>
        </div>
        <div class="door-list">
          <el-card 
            v-for="door in favoriteDoors" 
            :key="door.doorControlId"
            class="door-item"
            shadow="hover"
          >
            <div class="door-content">
              <el-icon 
                class="favorite-icon-absolute active"
                @click="toggleFavorite(door)"
                :title="'取消收藏'"
              >
                <StarFilled />
              </el-icon>
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
      </div>

      <!-- 全部门禁列表 -->
      <div v-if="displayDoors.length > 0">
        <div class="section-header" v-if="favoriteDoors.length > 0">
          <el-icon class="section-icon"><Menu /></el-icon>
          <span>其他门禁</span>
        </div>
        <div class="door-list">
          <el-card 
            v-for="door in displayDoors" 
            :key="door.doorControlId"
            class="door-item"
            shadow="hover"
          >
            <div class="door-content">
              <el-icon 
                :class="['favorite-icon-absolute', { 'active': isFavorite(door) }]"
                @click="toggleFavorite(door)"
                :title="isFavorite(door) ? '取消收藏' : '添加收藏'"
              >
                <StarFilled v-if="isFavorite(door)" />
                <Star v-else />
              </el-icon>
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
    </div>
    <el-empty v-else-if="currentDoors.length === 0" description="请选择社区查看门禁信息" />

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

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Star, StarFilled, Menu } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'
import api from '../api'
import AccountManagement from './AccountManagement.vue'
import { hexMd5 } from '../utils/md5'
import type { DoorInfo, LogItem } from '../types'

interface ExtendedDoorInfo extends DoorInfo {
    phone: string
    communityId: string
    opening: boolean
    password?: string
    expiryTime?: string
    supportsPassword?: boolean
}

const userStore = useUserStore()
const selectedCommunity = ref('')
const currentDoors = ref<ExtendedDoorInfo[]>([])
const logs = ref<LogItem[]>([])
const showAccountDialog = ref(false)
const favorites = ref<number[]>([])
const passwordTimers: Record<string, number> = {}
let supportedDevices: string[] | null = null

// 计算属性：收藏的门（按收藏顺序排序）
const favoriteDoors = computed(() => {
  const doorMap = new Map(currentDoors.value.map(door => [door.doorControlId, door]))
  return favorites.value
    .map(id => doorMap.get(id))
    .filter(door => door !== undefined) as ExtendedDoorInfo[]
})

// 计算属性：显示的门（未收藏的门）
const displayDoors = computed(() => {
  return currentDoors.value.filter(door => !favorites.value.includes(door.doorControlId))
})

// 获取支持密码设备列表
const getSupportedDevices = async (): Promise<string[]> => {
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
const checkDeviceSupport = async (deviceType?: string): Promise<boolean> => {
  if (!deviceType) return false
  const devices = await getSupportedDevices()
  return devices.includes(deviceType)
}

// 计算密码
const getDoorPassword = (mac: string, communityId: string, timestamp: number): string => {
  const s = mac + timestamp + communityId
  let key = hexMd5(s)
  key = key.replace(/[a-zA-Z]/g, '')
  key = key.slice(-4)
  return key
}

// 获取下一个整10分钟
const getNext10Minute = (): Date => {
  const now = new Date()
  const minutes = now.getMinutes()
  const next10Minutes = Math.ceil(minutes / 10) * 10
  now.setMinutes(next10Minutes, 0, 0)
  return now
}

// 获取当前10分钟时间段
const getCurrent10Minutes = (): Date => {
  const now = new Date()
  const minutes = now.getMinutes()
  const current10Minutes = Math.floor(minutes / 10) * 10
  now.setMinutes(current10Minutes, 0, 0)
  return now
}

// 更新门密码
const updateDoorPassword = async (communityId: string, door: ExtendedDoorInfo): Promise<void> => {
  try {
    if (passwordTimers[door.doorControlId]) {
      clearTimeout(passwordTimers[door.doorControlId])
      delete passwordTimers[door.doorControlId]
    }

    const expiryTime = getNext10Minute()
    const password = getDoorPassword(door.macAddress || '', communityId, getCurrent10Minutes().getTime())
    
    door.password = password
    door.expiryTime = `${expiryTime.getHours().toString().padStart(2, '0')}:${expiryTime.getMinutes().toString().padStart(2, '0')}`

    let timeUntilNextPeriod = expiryTime.getTime() - new Date().getTime()
    if (timeUntilNextPeriod <= 0) {
      timeUntilNextPeriod = 5000
    }
    
    passwordTimers[door.doorControlId] = window.setTimeout(() => {
      updateDoorPassword(communityId, door)
    }, timeUntilNextPeriod + 5000)
  } catch (error) {
    console.error('获取开门密码失败:', error)
    addLog(`获取${door.doorControlName}密码失败: ${(error as Error).message}`, false)
  }
}

// 处理社区选择变化
const handleCommunityChange = async (): Promise<void> => {
  // 清除所有定时器
  Object.values(passwordTimers).forEach(timer => clearTimeout(timer))
  Object.keys(passwordTimers).forEach(key => delete passwordTimers[key])
  
  if (!selectedCommunity.value) {
    currentDoors.value = []
    return
  }

  const [phone, communityId] = selectedCommunity.value.split('_')
  const allDoors: DoorInfo[] = userStore.doors[communityId]
  
  if (!allDoors) {
    currentDoors.value = []
    return
  }

  // 为每个门添加额外属性
  currentDoors.value = allDoors.map(door => ({
    ...door,
    phone,
    communityId,
    opening: false,
    password: undefined,
    expiryTime: undefined,
    supportsPassword: undefined
  }))

  // 检查并更新密码
  for (const door of currentDoors.value) {
    const supportsPassword = await checkDeviceSupport(door.deviceModel)
    door.supportsPassword = supportsPassword
    
    if (supportsPassword && door.macAddress) {
      await updateDoorPassword(communityId, door)
    }
  }

  // 保存选择到本地存储
  localStorage.setItem('communityId', selectedCommunity.value)
}

// 开门
const handleOpenDoor = async (door: ExtendedDoorInfo): Promise<void> => {
  try {
    door.opening = true
    const success = await api.openDoor(door.phone, door.communityId, door.doorControlId)
    
    if (success) {
      ElMessage.success(`开门成功(${door.doorControlName})`)
      addLog(`开门成功(${door.doorControlName})`, true)
    } else {
      ElMessage.error(`开门失败(${door.doorControlName}): ${success}`)
      addLog(`开门失败(${door.doorControlName}): ${success}`, false)
    }
  } catch (error) {
    ElMessage.error((error as Error).message)
    addLog((error as Error).message, false)
  } finally {
    door.opening = false
  }
}

// 添加日志
const addLog = (message: string, success: boolean = true): void => {
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

// 加载收藏列表
const loadFavorites = async (): Promise<void> => {
  try {
    // 从 localStorage 加载作为后备
    const savedLocal = localStorage.getItem('favoriteDoors')
    if (savedLocal) {
      favorites.value = JSON.parse(savedLocal)
    }
    
    // 尝试从服务器加载
    const users = userStore.users
    if (users && users.length > 0) {
      const allFavorites: number[] = []
      const seenIds = new Set<number>()
      for (const user of users) {
        try {
          const userFavorites = await api.getFavorites(user.phone)
          userFavorites.forEach(id => {
            if (!seenIds.has(id)) {
              allFavorites.push(id)
              seenIds.add(id)
            }
          })
        } catch (error) {
          console.error(`加载用户 ${user.phone} 的收藏失败:`, error)
        }
      }
      if (allFavorites.length > 0) {
        favorites.value = allFavorites
        // 同步到 localStorage
        localStorage.setItem('favoriteDoors', JSON.stringify(favorites.value))
      }
    }
  } catch (error) {
    console.error('加载收藏列表失败:', error)
  }
}

// 保存收藏列表
const saveFavorites = async (): Promise<void> => {
  try {
    // 保存到 localStorage
    localStorage.setItem('favoriteDoors', JSON.stringify(favorites.value))
    
    // 保存到服务器
    const users = userStore.users
    if (users && users.length > 0) {
      for (const user of users) {
        try {
          await api.saveFavorites(user.phone, favorites.value)
        } catch (error) {
          console.error(`保存用户 ${user.phone} 的收藏失败:`, error)
        }
      }
    }
  } catch (error) {
    console.error('保存收藏列表失败:', error)
  }
}

// 检查是否收藏
const isFavorite = (door: ExtendedDoorInfo): boolean => {
  return favorites.value.includes(door.doorControlId)
}

// 切换收藏状态
const toggleFavorite = (door: ExtendedDoorInfo): void => {
  const index = favorites.value.indexOf(door.doorControlId)
  if (index !== -1) {
    favorites.value.splice(index, 1)
    ElMessage.success(`已取消收藏 ${door.doorControlName}`)
  } else {
    favorites.value.push(door.doorControlId)
    ElMessage.success(`已收藏 ${door.doorControlName}`)
  }
  saveFavorites()
}

// 重新加载用户信息
const handleReload = async (): Promise<void> => {
  await userStore.loadUsers()
  // 如果当前选择的社区还存在，重新加载
  if (selectedCommunity.value) {
    await handleCommunityChange()
  }
}

// 初始化
onMounted(async () => {
  // 加载收藏列表
  await loadFavorites()
  
  // 尝试恢复上次选择的社区
  const savedCommunity = localStorage.getItem('communityId')
  if (savedCommunity && userStore.communities && userStore.communities[savedCommunity]) {
    selectedCommunity.value = savedCommunity
    handleCommunityChange()
  } else if (userStore.communities && Object.keys(userStore.communities).length > 0) {
    // 如果没有保存的社区或社区无效，选择第一个
    selectedCommunity.value = Object.keys(userStore.communities)[0]
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

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.header-actions .el-button.is-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.header-actions .el-button.is-circle .el-icon {
  margin: 0;
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
  
  .header-actions {
    width: 100%;
  }
  
  .header-actions .el-button:not(:first-child) {
    flex: 1;
  }
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 20px 0 16px 0;
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.section-header:first-child {
  margin-top: 0;
}

.section-icon {
  font-size: 20px;
  color: #409eff;
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
  position: relative;
}

.door-item :deep(.el-card__body) {
  position: relative;
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
  
  .door-info {
    padding-right: 35px;
  }
}

.door-info {
  flex: 1;
  padding-right: 35px;
}

.door-info h3 {
  margin: 0 0 12px 0;
  font-size: 18px;
  color: #303133;
}

.favorite-icon-absolute {
  position: absolute;
  top: 12px;
  right: 12px;
  font-size: 24px;
  cursor: pointer;
  color: #dcdfe6;
  transition: all 0.3s;
  z-index: 10;
}

.favorite-icon-absolute:hover {
  color: #ffd04b;
  transform: scale(1.2);
}

.favorite-icon-absolute.active {
  color: #ffd04b;
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
  
  .section-header {
    color: #e0e0e0;
  }
  
  .door-info h3 {
    color: #e0e0e0;
  }
  
  .expiry-time {
    color: #b1b3b8;
  }
  
  .favorite-icon-absolute {
    color: #4c4d4f;
  }
  
  .favorite-icon-absolute:hover {
    color: #ffd04b;
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
