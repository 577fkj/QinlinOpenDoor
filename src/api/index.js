import axios from 'axios'
import { ElMessage } from 'element-plus'

// 获取URL参数中的token
export function getAccessToken() {
  const urlParams = new URLSearchParams(window.location.search)
  let token = urlParams.get('token')
  if (!token) {
    const strs = window.location.href.split(':')
    if (strs.length >= 4) {
      token = strs[3]
    }
  }
  return token
}

// 添加token到URL
function addTokenToUrl(url) {
  const token = getAccessToken()
  if (!token) return url
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}token=${token}`
}

// 创建axios实例
const request = axios.create({
  timeout: 30000
})

// 响应拦截器
request.interceptors.response.use(
  response => {
    const data = response.data
    if (data.code !== 200) {
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message || '请求失败'))
    }
    return data.data
  },
  error => {
    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)

// API接口
export const api = {
  // 获取所有用户
  getAllUsers() {
    return request.get(addTokenToUrl('/get_all_users'))
  },

  // 发送验证码
  sendSmsCode(phone, userId = null) {
    let url = `/send_sms_code?phone=${phone}`
    if (userId) {
      url += `&user_id=${userId}`
    }
    return request.get(addTokenToUrl(url))
  },

  // 登录
  login(userId, phone, code) {
    return request.get(addTokenToUrl(`/login?user_id=${userId}&phone=${phone}&code=${code}`))
  },

  // 开门
  openDoor(userId, communityId, doorId) {
    return request.get(addTokenToUrl(`/open_door?user_id=${userId}&community_id=${communityId}&door_id=${doorId}`))
  },

  // 获取支持密码的设备列表
  getSupportPasswordDevices() {
    return request.get(addTokenToUrl('/get_support_password_devices'))
  },

  // 获取验证码（轮询）
  getSmsCode(userId) {
    return request.get(addTokenToUrl(`/get_sms_code?user_id=${userId}`))
  },

  // 更新自动重登配置
  updateAutoRelogin(userId, enabled) {
    return request.post(addTokenToUrl('/update_auto_relogin'), {
      user_id: userId,
      enabled: enabled
    })
  }
}

export default api
