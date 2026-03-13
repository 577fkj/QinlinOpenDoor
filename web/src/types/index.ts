// 通用响应类型
export interface ApiResponse<T = any> {
  code: number
  message?: string
  data: T
}

// 用户信息
export interface UserInfo {
    id: number
    mobile: string
    nickName: string
    portraitUrl: string
    realName: string
    userName: string
    hasFaceKey: number
}

// 社区信息
export interface CommunityInfo {
    buildingName: string
    cityName: string
    communityCode: string
    communityId: number
    communityName: string
    districtName: string
    expiryDate: string
    houseId: string
    houseNo: string
    provinceName: string
}

// 社区数据
export interface Community {
    info: CommunityInfo
    doors: DoorInfo[]
}

// 门禁信息
export interface DoorInfo {
    deviceModel: string
    customDoorControlName: string
    doorControlId: number
    doorControlName: string
    macAddress: string
    online: string
}

// 用户数据
export interface UserData {
  phone: string
  is_online: boolean
  info?: UserInfo
  communities?: Community[]
  auto_relogin: boolean
  updating: boolean
}

// 短信验证码响应
export interface SmsCodeResponse {
  success: boolean
  message?: string
}

// 获取验证码响应
export interface GetSmsCodeResponse {
  code?: string
  login_success?: boolean
}

// 登录表单
export interface LoginForm {
  phone: string
  code: string
}

// 操作日志
export interface LogItem {
  time: string
  message: string
  success: boolean
}

// 电子围栏
export interface GeoFence {
  name: string
  points: [number, number][]  // [lng, lat][]
}

// 电子围栏Map: phone -> communityId -> GeoFence
export type GeoFenceMap = Record<string, Record<string, GeoFence>>
