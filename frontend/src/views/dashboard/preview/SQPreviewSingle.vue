<script setup lang="ts">
import SQPreview from '@/views/dashboard/preview/SQPreview.vue'
import { load_resource_prepare } from '@/views/dashboard/utils/canvasUtils.ts'
import { reactive, ref, watch } from 'vue'
import router from '@/router'

const previewCanvasContainer = ref(null)
const dashboardPreview = ref(null)
const dataInitState = ref(true)
const downloadStatus = ref(false)
const state = reactive({
  resourceId: null as string | null,
  canvasDataPreview: [],
  canvasStylePreview: {},
  canvasViewInfoPreview: {},
  dashboardInfo: {},
})

watch(
  () => router.currentRoute.value.query.resourceId,
  (resourceId) => {
    state.resourceId = Array.isArray(resourceId) ? (resourceId[0] ?? null) : (resourceId ?? null)
    if (state.resourceId) {
      loadCanvasData({ id: state.resourceId })
    }
  },
  { immediate: true }
)

const loadCanvasData = (params: any) => {
  dataInitState.value = false
  load_resource_prepare(
    { id: params.id },
    function ({ dashboardInfo, canvasDataResult, canvasStyleResult, canvasViewInfoPreview }) {
      state.canvasDataPreview = canvasDataResult
      state.canvasStylePreview = canvasStyleResult
      state.canvasViewInfoPreview = canvasViewInfoPreview
      state.dashboardInfo = dashboardInfo
      dataInitState.value = true
    }
  )
}
</script>

<template>
  <div id="sq-preview-content" ref="previewCanvasContainer" class="content">
    <SQPreview
      v-if="state.canvasStylePreview && dataInitState"
      ref="dashboardPreview"
      :dashboard-info="state.dashboardInfo"
      :component-data="state.canvasDataPreview"
      :canvas-style-data="state.canvasStylePreview"
      :canvas-view-info="state.canvasViewInfoPreview"
      :download-status="downloadStatus"
    ></SQPreview>
  </div>
</template>

<style scoped lang="less">
.content {
  position: relative;
  display: flex;
  width: 100%;
  height: 100vh;
  overflow-x: hidden;
  overflow-y: auto;
  align-items: center;
}
</style>
