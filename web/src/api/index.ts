import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResponse, UserData, SmsCodeResponse, GetSmsCodeResponse, GeoFenceMap } from '../types'

// 从全局变量获取动态 token
const apiToken = window.API_TOKEN || ''

// 创建axios实例
const request: AxiosInstance = axios.create({
  baseURL: apiToken ? `/${apiToken}/api` : '/api',
  timeout: 30000
})

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const data = response.data
    // 检查业务状态码
    if (data.code !== 200) {
      const errorMsg = data.message || '请求失败'
      ElMessage.error(errorMsg)
      return Promise.reject(new Error(errorMsg))
    }
    return data.data
  },
  (error: AxiosError<ApiResponse>) => {
    // 处理HTTP错误
    let errorMsg = '网络错误'
    if (error.response) {
      // 服务器返回了错误响应
      const data = error.response.data
      if (data && data.message) {
        errorMsg = data.message
      } else if (error.response.status) {
        errorMsg = `请求错误 ${error.response.status}`
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      errorMsg = '服务器无响应'
    } else {
      // 请求配置出错
      errorMsg = error.message || '请求配置错误'
    }
    ElMessage.error(errorMsg)
    return Promise.reject(error)
  }
)

// API接口
export const api = {
  // 获取所有用户
  getAllUsers(): Promise<UserData[]> {
    return request.get('/get_all_users')
  },

  // 发送验证码
  sendSmsCode(phone: string): Promise<SmsCodeResponse> {
    return request.get(`/send_sms_code?phone=${phone}`)
  },

  // 登录
  login(phone: string, code: string): Promise<boolean> {
    return request.get(`/login?phone=${phone}&code=${code}`)
  },

  // 开门
  openDoor(phone: string, communityId: string, doorId: string | number): Promise<boolean> {
    return request.get(`/open_door?phone=${phone}&community_id=${communityId}&door_id=${doorId}`)
  },

  // 获取支持密码的设备列表
  getSupportPasswordDevices(): Promise<string[]> {
    return request.get('/get_support_password_devices')
  },

  // 获取验证码（轮询）
  getSmsCode(phone: string): Promise<GetSmsCodeResponse> {
    return request.get(`/get_sms_code?phone=${phone}`)
  },

  // 更新自动重登配置
  updateAutoRelogin(phone: string, enabled: boolean): Promise<void> {
    return request.post('/update_auto_relogin', {
      phone: phone,
      enabled: enabled
    })
  },

  // 获取收藏列表
  getFavorites(phone: string): Promise<number[]> {
    return request.get(`/get_favorites?phone=${phone}`)
  },

  // 保存收藏列表
  saveFavorites(phone: string, favorites: number[]): Promise<void> {
    return request.post('/save_favorites', {
      phone: phone,
      favorites: favorites
    })
  },

  // 获取高德地图Key
  getAmapKey(): Promise<string> {
    return request.get('/get_amap_key')
  },

  // 获取所有电子围栏
  getGeofences(): Promise<GeoFenceMap> {
    return request.get('/get_geofences')
  },

  // 保存电子围栏
  saveGeofence(phone: string, communityId: string, name: string, points: [number, number][]): Promise<void> {
    return request.post('/save_geofence', {
      phone: phone,
      community_id: communityId,
      name: name,
      points: points
    })
  },

  // 删除电子围栏
  deleteGeofence(phone: string, communityId: string): Promise<void> {
    return request.post('/delete_geofence', {
      phone: phone,
      community_id: communityId
    })
  }
}

export default api
