import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useUserStore = defineStore('user', () => {
  const users = ref([])
  const doors = ref({})
  const communities = ref({})

  // 加载用户信息
  async function loadUsers() {
    try {
      const data = await api.getAllUsers()
      users.value = data
      
      // 处理门和社区信息
      doors.value = {}
      communities.value = {}
      
      for (const user of data) {
        if (user.all_door) {
          for (const communityId in user.all_door) {
            doors.value[communityId] = user.all_door[communityId]
          }
        }
        if (user.community_info && user.community_info.length > 0) {
          for (const community of user.community_info) {
            communities.value[user.index] = community
          }
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
