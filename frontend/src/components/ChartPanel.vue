<template>
  <div class="chart-wrap" ref="rootRef">
    <v-chart v-if="ready && localOption" class="chart-box" :option="localOption" autoresize @click="onClick" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, LineChart, PieChart, ScatterChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import VChart from "vue-echarts";

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  DataZoomComponent,
]);

const props = defineProps<{ option: Record<string, unknown>; lazy?: boolean }>();
const emit = defineEmits<{ click: [payload: { name: string }] }>();

const rootRef = ref<HTMLElement>();
const ready = ref(!props.lazy);
const localOption = ref<Record<string, unknown> | null>(props.option || null);
let observer: IntersectionObserver | null = null;
let worker: Worker | null = null;

function separateLegendAndZoom(option: Record<string, unknown>) {
  const zooms = Array.isArray(option.dataZoom) ? (option.dataZoom as Record<string, unknown>[]) : [];
  const hasSlider = zooms.some((item) => item?.type === "slider");
  const legend = option.legend as Record<string, unknown> | undefined;
  if (!hasSlider || !legend || legend.show === false || legend.top !== undefined) return option;
  return {
    ...option,
    legend: { ...legend, bottom: 32 },
    dataZoom: zooms.map((item) => (item?.type === "slider" ? { ...item, bottom: 6, showDetail: false } : item)),
    grid: { ...((option.grid as Record<string, unknown>) || {}), bottom: 88 },
  };
}

function applyOption(option: Record<string, unknown> | null | undefined) {
  if (!option) {
    localOption.value = null;
    return;
  }
  const laidOut = separateLegendAndZoom(option);
  localOption.value = laidOut;
  if (typeof Worker === "undefined") return;
  try {
    worker?.terminate();
    worker = new Worker(new URL("../workers/downsample.ts", import.meta.url), { type: "module" });
    worker.onmessage = (event: MessageEvent<Record<string, unknown>>) => {
      if (event.data) localOption.value = separateLegendAndZoom(event.data);
    };
    worker.onerror = () => {
      localOption.value = laidOut;
    };
    worker.postMessage({ option: laidOut });
  } catch {
    localOption.value = laidOut;
  }
}

watch(
  () => props.option,
  (option) => applyOption(option),
  { deep: true }
);

function onClick(params: any) {
  const name = params?.name ?? params?.data?.name;
  if (name !== undefined && name !== null && String(name)) {
    emit("click", { name: String(name) });
  }
}

onMounted(() => {
  applyOption(props.option);
  if (!props.lazy) {
    ready.value = true;
    return;
  }
  if (!rootRef.value) {
    ready.value = true;
    return;
  }
  observer = new IntersectionObserver((entries) => {
    if (entries.some((item) => item.isIntersecting)) {
      ready.value = true;
      observer?.disconnect();
    }
  });
  observer.observe(rootRef.value);
  window.setTimeout(() => {
    if (!ready.value) ready.value = true;
  }, 400);
});

onBeforeUnmount(() => {
  observer?.disconnect();
  worker?.terminate();
});
</script>

<style scoped>
.chart-wrap {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 280px;
}
.chart-box {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  min-height: 280px;
}
</style>
