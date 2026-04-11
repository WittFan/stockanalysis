<template>
  <div ref="el" class="echart-container"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['chart-ready'])

const el = ref(null)
let chart = null

onMounted(() => {
  chart = echarts.init(el.value)
  chart.setOption(props.option)
  emit('chart-ready', chart)
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  chart?.dispose()
  window.removeEventListener('resize', resize)
})

watch(() => props.option, opt => {
  chart?.setOption(opt, { notMerge: true })
}, { deep: true })

function resize() { chart?.resize() }

defineExpose({ getInstance: () => chart })
</script>

<style scoped>
.echart-container { width: 100%; height: 100%; }
</style>
