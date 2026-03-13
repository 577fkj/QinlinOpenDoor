import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'
import type { UserData, DoorInfo, CommunityInfo } from '../types'

export const useUserStore = defineStore('user', () => {
  const users = ref<UserData[]>([])
  const doors = ref<Record<string, DoorInfo[]>>({})
  const communities = ref<Record<string, CommunityInfo & { phone: string }>>({})

  // 加载用户信息
  async function loadUsers(): Promise<UserData[]> {
    try {
      const data = await api.getAllUsers()
      users.value = data
      
      // 处理门和社区信息
      doors.value = {}
      communities.value = {}
      
      for (const user of data) {
        for (const community of user.communities || []) {
          const key = `${user.phone}_${community.info.communityId}`
          communities.value[key] = {
            ...community.info,
            phone: user.phone
          }
          doors.value[community.info.communityId] = community.doors
        }
      }
      
      return data
    } catch (error) {
      console.error('加载用户信息失败:', error)
      throw error
    }
  }

  return {
    users,
    doors,
    communities,
    loadUsers
  }
})
