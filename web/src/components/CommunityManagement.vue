<template>
  <el-dialog
    v-model="visible"
    title="社区管理"
    :width="dialogWidth"
    class="community-dialog"
    @close="handleClose"
    destroy-on-close
  >
    <!-- 社区列表 -->
    <div class="community-list">
      <el-card
        v-for="(community, key) in communities"
        :key="key"
        class="community-card"
        shadow="hover"
      >
        <div class="community-item">
          <div class="community-info">
            <div class="community-name">{{ community.communityName }}</div>
            <div class="community-detail">
              {{ community.provinceName }}{{ community.cityName }}{{ community.districtName }}
            </div>
            <div class="fence-status">
              <el-tag v-if="getFence(key as string)" type="success" size="small">已设围栏</el-tag>
              <el-tag v-else type="info" size="small">未设围栏</el-tag>
            </div>
          </div>
          <div class="community-actions">
            <el-button size="small" type="primary" @click="openFenceEditor(key, community)">
              {{ getFence(key as string) ? '编辑围栏' : '设置围栏' }}
            </el-button>
            <el-button
              v-if="getFence(key as string)"
              size="small"
              type="danger"
              @click="handleDeleteFence(key)"
            >
              删除围栏
            </el-button>
          </div>
        </div>
      </el-card>
      <el-empty v-if="Object.keys(communities).length === 0" description="暂无社区" />
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>

  <!-- 围栏编辑对话框（全屏地图） -->
  <el-dialog
    v-model="showFenceEditor"
    :title="`设置围栏 - ${editingCommunityName}`"
    :width="dialogWidth"
    class="fence-editor-dialog"
    destroy-on-close
    @opened="initMap"
    @close="cleanupMap"
  >
    <div class="fence-editor">
      <div class="map-toolbar">
        <el-button size="small" type="primary" @click="startDrawing" :disabled="isDrawing">
          {{ currentPoints.length > 0 ? '重新绘制' : '开始绘制' }}
        </el-button>
        <el-button size="small" @click="clearDrawing" :disabled="currentPoints.length === 0">
          清除
        </el-button>
        <el-button size="small" @click="locateMe" :loading="locating">
          定位到当前位置
        </el-button>
        <span class="draw-tip" v-if="isDrawing">点击地图添加围栏顶点，双击完成绘制</span>
        <span class="draw-tip" v-else-if="currentPoints.length > 0">
          围栏已绘制（{{ currentPoints.length }}个顶点）
        </span>
      </div>
      <div ref="mapContainer" class="map-container"></div>
    </div>

    <template #footer>
      <el-button @click="showFenceEditor = false">取消</el-button>
      <el-button
        type="primary"
        :loading="saving"
        :disabled="currentPoints.length < 3"
        @click="handleSaveFence"
      >
        保存围栏
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'
import api from '../api'
import type { CommunityInfo, GeoFence, GeoFenceMap } from '../types'

interface Props {
  modelValue: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'fencesUpdated': []
}>()

const userStore = useUserStore()

const visible = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

const windowWidth = ref(window.innerWidth)
const dialogWidth = computed(() => windowWidth.value < 768 ? '95%' : '700px')

const handleResize = () => { windowWidth.value = window.innerWidth }
window.addEventListener('resize', handleResize)
onUnmounted(() => window.removeEventListener('resize', handleResize))

// 社区列表（来自user store）
const communities = computed(() => userStore.communities)

// 围栏数据
const geofences = ref<GeoFenceMap>({})
const showFenceEditor = ref(false)
const editingPhone = ref('')
const editingCommunityId = ref('')
const editingCommunityName = ref('')

// 从嵌套结构中获取围栏
const getFence = (key: string): GeoFence | undefined => {
  const parts = key.split('_')
  const communityId = parts.pop()!
  const phone = parts.join('_')
  return geofences.value[phone]?.[communityId]
}
const currentPoints = ref<[number, number][]>([])
const isDrawing = ref(false)
const saving = ref(false)
const locating = ref(false)

// 高德地图相关
const mapContainer = ref<HTMLDivElement | null>(null)
let mapInstance: any = null
let currentPolygon: any = null
let drawingHandler: any = null
let AMapRef: any = null
let locationMarker: any = null
let accuracyCircle: any = null

// WGS84 → GCJ02 坐标转换
const _PI = Math.PI
const _A = 6378245.0
const _EE = 0.00669342162296594323

const _transLat = (x: number, y: number): number => {
  let r = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x))
  r += (20.0 * Math.sin(6.0 * x * _PI) + 20.0 * Math.sin(2.0 * x * _PI)) * 2.0 / 3.0
  r += (20.0 * Math.sin(y * _PI) + 40.0 * Math.sin(y / 3.0 * _PI)) * 2.0 / 3.0
  r += (160.0 * Math.sin(y / 12.0 * _PI) + 320.0 * Math.sin(y * _PI / 30.0)) * 2.0 / 3.0
  return r
}

const _transLng = (x: number, y: number): number => {
  let r = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x))
  r += (20.0 * Math.sin(6.0 * x * _PI) + 20.0 * Math.sin(2.0 * x * _PI)) * 2.0 / 3.0
  r += (20.0 * Math.sin(x * _PI) + 40.0 * Math.sin(x / 3.0 * _PI)) * 2.0 / 3.0
  r += (150.0 * Math.sin(x / 12.0 * _PI) + 300.0 * Math.sin(x / 30.0 * _PI)) * 2.0 / 3.0
  return r
}

const wgs84ToGcj02 = (wgsLng: number, wgsLat: number): [number, number] => {
  let dLat = _transLat(wgsLng - 105.0, wgsLat - 35.0)
  let dLng = _transLng(wgsLng - 105.0, wgsLat - 35.0)
  const radLat = wgsLat / 180.0 * _PI
  let magic = Math.sin(radLat)
  magic = 1 - _EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtMagic) * _PI)
  dLng = (dLng * 180.0) / (_A / sqrtMagic * Math.cos(radLat) * _PI)
  return [wgsLng + dLng, wgsLat + dLat]
}

// 加载围栏数据
const loadGeofences = async () => {
  try {
    geofences.value = await api.getGeofences()
  } catch (error) {
    console.error('加载围栏数据失败:', error)
  }
}

// 监听对话框打开
watch(visible, async (val) => {
  if (val) {
    await loadGeofences()
  }
})

// 加载高德地图JS API
const loadAMapScript = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    if ((window as any).AMap) {
      AMapRef = (window as any).AMap
      resolve()
      return
    }
    const existingScript = document.querySelector('script[src*="amap"]')
    if (existingScript) {
      existingScript.addEventListener('load', () => {
        AMapRef = (window as any).AMap
        resolve()
      })
      return
    }

    // 使用高德地图JS API 2.0，Key 从 .env.local 的 VITE_AMAP_KEY 读取
    const AMAP_KEY = import.meta.env.VITE_AMAP_KEY || ''
    if (!AMAP_KEY) {
      reject(new Error('未配置高德地图Key，请在 web/.env.local 中设置 VITE_AMAP_KEY'))
      return
    }
    ;(window as any)._AMapSecurityConfig = { securityJsCode: '' }
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${AMAP_KEY}&plugin=AMap.Geolocation,AMap.MouseTool`
    script.onload = () => {
      AMapRef = (window as any).AMap
      resolve()
    }
    script.onerror = () => reject(new Error('高德地图JS API加载失败'))
    document.head.appendChild(script)
  })
}

// 初始化地图
const initMap = async () => {
  try {
    await loadAMapScript()

    if (!mapContainer.value) return

    mapInstance = new AMapRef.Map(mapContainer.value, {
      zoom: 16,
      center: [116.397428, 39.90923], // 北京天安门默认
      mapStyle: window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'amap://styles/dark'
        : 'amap://styles/normal'
    })

    // 如果已有围栏数据，显示到地图上
    const existingFence = geofences.value[editingPhone.value]?.[editingCommunityId.value]
    if (existingFence && existingFence.points.length >= 3) {
      currentPoints.value = existingFence.points as [number, number][]
      drawPolygon(currentPoints.value)
      // 自适应显示
      mapInstance.setFitView()
    }
    // 自动定位当前用户位置
    locateMe()
  } catch (error) {
    ElMessage.error('地图初始化失败: ' + (error as Error).message)
  }
}

// 清理地图
const cleanupMap = () => {
  if (drawingHandler) {
    drawingHandler.close(true)
    drawingHandler = null
  }
  if (mapInstance) {
    mapInstance.destroy()
    mapInstance = null
  }
  currentPolygon = null
  locationMarker = null
  accuracyCircle = null
  isDrawing.value = false
  currentPoints.value = []
}

// 显示当前位置标记
const showLocationMarker = (lnglat: any, accuracy?: number) => {
  if (!mapInstance || !AMapRef) return

  // 移除旧标记
  if (locationMarker) mapInstance.remove(locationMarker)
  if (accuracyCircle) mapInstance.remove(accuracyCircle)

  // 蓝色圆点标记
  locationMarker = new AMapRef.Marker({
    position: lnglat,
    content: '<div style="width:14px;height:14px;background:#4285F4;border:3px solid #fff;border-radius:50%;box-shadow:0 0 6px rgba(66,133,244,0.6);"></div>',
    offset: new AMapRef.Pixel(-10, -10),
    zIndex: 200
  })
  mapInstance.add(locationMarker)

  // 精度圈
  if (accuracy && accuracy > 0) {
    accuracyCircle = new AMapRef.Circle({
      center: lnglat,
      radius: accuracy,
      strokeColor: '#4285F4',
      strokeWeight: 1,
      strokeOpacity: 0.3,
      fillColor: '#4285F4',
      fillOpacity: 0.1,
      zIndex: 100
    })
    mapInstance.add(accuracyCircle)
  }
}

// 定位
const locateMe = async () => {
  if (!mapInstance || !AMapRef) return
  locating.value = true
  try {
    // 先尝试浏览器原生定位（返回WGS84坐标，需转GCJ02给高德地图使用）
    if (navigator.geolocation) {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 8000,
          maximumAge: 0
        })
      })
      const [gcjLng, gcjLat] = wgs84ToGcj02(pos.coords.longitude, pos.coords.latitude)
      const lnglat = new AMapRef.LngLat(gcjLng, gcjLat)
      showLocationMarker(lnglat, pos.coords.accuracy)
      mapInstance.setCenter(lnglat)
      mapInstance.setZoom(17)
    }
  } catch {
    // 降级到高德定位
    const geolocation = new AMapRef.Geolocation({
      enableHighAccuracy: true,
      timeout: 10000
    })
    geolocation.getCurrentPosition((status: string, result: any) => {
      if (status === 'complete') {
        showLocationMarker(result.position, result.accuracy)
        mapInstance.setCenter(result.position)
        mapInstance.setZoom(17)
      } else {
        ElMessage.warning('定位失败，请手动拖动地图')
      }
    })
  } finally {
    locating.value = false
  }
}

// 开始绘制
const startDrawing = () => {
  if (!mapInstance || !AMapRef) return
  clearDrawing()
  isDrawing.value = true

  drawingHandler = new AMapRef.MouseTool(mapInstance)
  drawingHandler.polygon({
    strokeColor: '#409EFF',
    strokeWeight: 3,
    strokeOpacity: 0.8,
    fillColor: '#409EFF',
    fillOpacity: 0.25
  })

  drawingHandler.on('draw', (event: any) => {
    isDrawing.value = false
    const path = event.obj.getPath()
    currentPoints.value = path.map((p: any) => [p.lng, p.lat] as [number, number])
    currentPolygon = event.obj
    drawingHandler.close(false)
  })
}

// 清除绘制
const clearDrawing = () => {
  if (drawingHandler) {
    drawingHandler.close(true)
  }
  if (currentPolygon) {
    mapInstance.remove(currentPolygon)
    currentPolygon = null
  }
  currentPoints.value = []
  isDrawing.value = false
}

// 绘制多边形（用于显示已有围栏）
const drawPolygon = (points: [number, number][]) => {
  if (!mapInstance || !AMapRef || points.length < 3) return

  if (currentPolygon) {
    mapInstance.remove(currentPolygon)
  }

  const path = points.map(([lng, lat]) => new AMapRef.LngLat(lng, lat))
  currentPolygon = new AMapRef.Polygon({
    path,
    strokeColor: '#409EFF',
    strokeWeight: 3,
    strokeOpacity: 0.8,
    fillColor: '#409EFF',
    fillOpacity: 0.25
  })
  mapInstance.add(currentPolygon)
}

// 打开围栏编辑器
const openFenceEditor = (_key: string, community: CommunityInfo & { phone: string }) => {
  editingPhone.value = community.phone
  editingCommunityId.value = String(community.communityId)
  editingCommunityName.value = community.communityName
  showFenceEditor.value = true
}

// 保存围栏
const handleSaveFence = async () => {
  if (currentPoints.value.length < 3) {
    ElMessage.warning('请至少绘制3个顶点')
    return
  }
  saving.value = true
  try {
    await api.saveGeofence(editingPhone.value, editingCommunityId.value, editingCommunityName.value, currentPoints.value)
    ElMessage.success('围栏保存成功')
    await loadGeofences()
    showFenceEditor.value = false
    emit('fencesUpdated')
  } catch (error) {
    console.error('保存围栏失败:', error)
  } finally {
    saving.value = false
  }
}

// 删除围栏
const handleDeleteFence = async (key: string) => {
  try {
    await ElMessageBox.confirm('确定删除该社区的电子围栏？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    const parts = key.split('_')
    const communityId = parts.pop()!
    const phone = parts.join('_')
    await api.deleteGeofence(phone, communityId)
    ElMessage.success('围栏已删除')
    await loadGeofences()
    emit('fencesUpdated')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除围栏失败:', error)
    }
  }
}

const handleClose = () => {
  visible.value = false
}
</script>

<style scoped>
.community-list {
  max-height: 500px;
  overflow-y: auto;
}

.community-card {
  margin-bottom: 12px;
  border: none;
}

.community-card:last-child {
  margin-bottom: 0;
}

.community-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.community-info {
  flex: 1;
}

.community-name {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.community-detail {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.fence-status {
  margin-top: 6px;
}

.community-actions {
  display: flex;
  gap: 8px;
}

.fence-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.map-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.draw-tip {
  font-size: 13px;
  color: #909399;
}

.map-container {
  width: 100%;
  height: 450px;
  border-radius: 8px;
  border: 1px solid #dcdfe6;
}

@media (max-width: 768px) {
  .community-item {
    flex-direction: column;
    align-items: stretch;
  }

  .community-actions {
    width: 100%;
  }

  .community-actions .el-button {
    flex: 1;
  }

  .map-container {
    height: 350px;
  }

  .map-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}

/* 深色模式 */
@media (prefers-color-scheme: dark) {
  .community-name {
    color: #e0e0e0;
  }

  .community-detail {
    color: #b1b3b8;
  }

  .map-container {
    border-color: #4c4d4f;
  }
}
</style>
