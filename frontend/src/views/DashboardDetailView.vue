<template>
  <div class="dash">
    <div class="hero">
      <div>
        <p class="kicker">经营分析看板</p>
        <h2>{{ dashboard?.title || "仪表盘详情" }}</h2>
        <p class="sub">{{ dashboard?.description }}</p>
      </div>
      <div class="hero-actions">
        <el-tag v-if="filterValue" closable @close="clearFilter">筛选：{{ filterValue }}</el-tag>
        <el-button @click="saveLayout">保存布局</el-button>
        <el-button @click="share">生成分享链接</el-button>
        <el-button type="primary" @click="exportPdf">导出 PDF</el-button>
        <el-button @click="$router.push('/dashboards')">返回</el-button>
      </div>
    </div>
    <div class="kpis" v-if="kpis.length">
      <div v-for="item in kpis" :key="item.label" class="kpi">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </div>
    </div>
    <ConclusionPanel :text="boardConclusion" />
    <p class="hint">拖拽缩放卡片。点击某个分类/日期，其它图表会按同一维度过滤。</p>
    <div ref="boardRef" class="board">
      <GridLayout v-model:layout="layout" :col-num="12" :row-height="30" :is-draggable="true" :is-resizable="true">
        <GridItem v-for="item in layout" :key="item.i" :x="item.x" :y="item.y" :w="item.w" :h="item.h" :i="item.i">
          <el-card class="tile" shadow="never">
            <div class="tile-head">
              <strong>{{ chartMap[item.chart_id]?.title }}</strong>
              <el-tag size="small" type="info">{{ typeLabel(chartMap[item.chart_id]?.chart_type) }}</el-tag>
            </div>
            <ChartPanel
              v-if="chartMap[item.chart_id]"
              lazy
              :option="chartMap[item.chart_id].option"
              @click="onChartClick(chartMap[item.chart_id], $event)"
            />
          </el-card>
        </GridItem>
      </GridLayout>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { GridItem, GridLayout } from "grid-layout-plus";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import { chartApi, dashboardApi, type ChartItem, type DashboardItem, type LayoutItem } from "../api";
import ChartPanel from "../components/ChartPanel.vue";
import ConclusionPanel from "../components/ConclusionPanel.vue";

const route = useRoute();
const dashboard = ref<DashboardItem>();
const charts = ref<ChartItem[]>([]);
const layout = ref<LayoutItem[]>([]);
const filterField = ref("");
const filterValue = ref("");
const boardRef = ref<HTMLElement>();
const chartMap = computed(() => Object.fromEntries(charts.value.map((item) => [item.id, item])));
const kpis = computed(() => {
  if (dashboard.value?.kpis?.length) return dashboard.value.kpis;
  return fallbackKpis.value;
});
const fallbackKpis = computed(() => {
  const items: { label: string; value: string | number; hint?: string }[] = [
    { label: "图表数量", value: charts.value.length, hint: "当前看板" },
  ];
  for (const chart of charts.value.slice(0, 3)) {
    const series = (chart.option?.series as any[])?.[0];
    const raw = (series?.data || []) as any[];
    const nums = raw.map((item) => (typeof item === "object" ? Number(item?.value) : Number(item))).filter((n) => !Number.isNaN(n));
    if (!nums.length) continue;
    const sum = nums.reduce((a, b) => a + b, 0);
    items.push({ label: chart.title, value: Number(sum.toFixed(2)), hint: "当前视图合计" });
  }
  return items.slice(0, 4);
});
const boardConclusion = computed(() => {
  if (dashboard.value?.conclusion) return dashboard.value.conclusion;
  return charts.value
    .map((item) => item.insight)
    .filter(Boolean)
    .slice(0, 3)
    .join("\n");
});

function typeLabel(type?: string) {
  return ({ bar: "柱状对比", line: "趋势", pie: "结构占比", scatter: "相关分析" } as Record<string, string>)[type || ""] || "图表";
}

async function loadCharts() {
  const filter = filterField.value ? { field: filterField.value, value: filterValue.value } : undefined;
  const { data } = await chartApi.list(filter);
  charts.value = data;
}

async function load() {
  const id = Number(route.params.id);
  const { data } = await dashboardApi.get(id);
  dashboard.value = data;
  layout.value = data.layout?.length
    ? data.layout
    : data.chart_ids.map((cid, index) => ({
        i: String(cid),
        x: (index % 2) * 6,
        y: Math.floor(index / 2) * 8,
        w: 6,
        h: 8,
        chart_id: cid,
      }));
  await loadCharts();
}

async function onChartClick(chart: ChartItem, payload: { name: string }) {
  filterField.value = chart.x_field;
  filterValue.value = payload.name;
  await loadCharts();
}

function clearFilter() {
  filterField.value = "";
  filterValue.value = "";
  loadCharts();
}

async function saveLayout() {
  if (!dashboard.value) return;
  await dashboardApi.update(dashboard.value.id, { layout: layout.value, chart_ids: dashboard.value.chart_ids });
  ElMessage.success("布局已保存为模板");
}

async function share() {
  if (!dashboard.value) return;
  const { data } = await dashboardApi.share(dashboard.value.id);
  const url = `${window.location.origin}${data.path}`;
  await navigator.clipboard.writeText(url);
  ElMessage.success(`分享链接已复制：${url}`);
}

async function exportPdf() {
  if (!boardRef.value) return;
  const canvas = await html2canvas(boardRef.value, { scale: 1.2 });
  const img = canvas.toDataURL("image/png");
  const pdf = new jsPDF("l", "pt", "a4");
  const width = pdf.internal.pageSize.getWidth();
  const height = (canvas.height * width) / canvas.width;
  pdf.addImage(img, "PNG", 0, 0, width, height);
  pdf.save(`${dashboard.value?.title || "dashboard"}.pdf`);
}

onMounted(load);
</script>

<style scoped>
.dash {
  padding-bottom: 24px;
}
.hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 20px;
  border-radius: 16px;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #2563eb 100%);
  color: #fff;
  margin-bottom: 16px;
}
.kicker {
  margin: 0;
  font-size: 12px;
  letter-spacing: 1px;
  color: #93c5fd;
}
.hero h2 {
  margin: 6px 0;
}
.sub {
  margin: 0;
  max-width: 720px;
  color: #cbd5e1;
  white-space: pre-wrap;
  font-size: 13px;
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
.kpi {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 16px;
}
.kpi span,
.kpi small {
  display: block;
  color: #64748b;
  font-size: 12px;
}
.kpi strong {
  display: block;
  margin: 6px 0 4px;
  font-size: 22px;
  color: #0f172a;
}
.hint {
  color: #64748b;
  font-size: 13px;
}
.board {
  background: #f8fafc;
  min-height: 480px;
  padding: 8px;
  border-radius: 12px;
}
.tile {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
}
.tile-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.tile :deep(.chart-wrap),
.tile :deep(.chart-box) {
  flex: 1;
  min-height: 180px;
  height: auto;
}
:deep(.vgl-item) {
  box-sizing: border-box;
}
</style>
