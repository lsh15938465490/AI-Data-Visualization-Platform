<template>
  <div class="dash" v-loading="loading">
    <header class="toolbar">
      <div class="toolbar-left">
        <el-button text @click="goBack">
          <el-icon><Back /></el-icon>
          返回列表
        </el-button>
        <div class="titles">
          <p class="kicker">经营分析看板 · 演示数据</p>
          <h2>{{ dashboard?.title || "仪表盘详情" }}</h2>
        </div>
        <el-tag type="primary" effect="plain" round>{{ chartCount }} 张图表</el-tag>
        <el-radio-group v-model="mode" size="small">
          <el-radio-button label="preview">预览模式</el-radio-button>
          <el-radio-button label="edit">编辑模式</el-radio-button>
        </el-radio-group>
      </div>
      <div class="toolbar-actions">
        <el-button v-if="editing" type="primary" :loading="saving" @click="saveLayout">保存布局</el-button>
        <el-button @click="share">生成分享链接</el-button>
        <el-button type="primary" @click="exportPdf">导出 PDF</el-button>
      </div>
    </header>

    <section class="filter-bar">
      <div class="filter-fields">
        <span class="filter-label">全局筛选</span>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          unlink-panels
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          clearable
        />
        <el-select v-model="region" placeholder="全部区域" clearable style="width: 160px">
          <el-option v-for="item in regionOptions" :key="item" :label="item" :value="item" />
        </el-select>
      </div>
      <div class="filter-tags" v-if="activeTags.length">
        <el-tag v-for="tag in activeTags" :key="tag.key" closable type="warning" effect="plain" @close="clearTag(tag.key)">
          {{ tag.label }}
        </el-tag>
        <el-button link type="primary" @click="clearAllFilters">清除筛选</el-button>
      </div>
    </section>

    <section class="kpis" v-if="kpis.length">
      <el-tooltip v-for="item in kpis" :key="item.label" :content="kpiTip(item)" placement="top">
        <article class="kpi">
          <div class="kpi-icon" :class="kpiTone(item.label)">
            <el-icon :size="18"><component :is="kpiIcon(item.label)" /></el-icon>
          </div>
          <div class="kpi-body">
            <span class="kpi-label">{{ item.label }}</span>
            <strong>{{ formatKpi(item.value) }}</strong>
            <small>{{ item.hint }}</small>
          </div>
        </article>
      </el-tooltip>
    </section>

    <ConclusionPanel
      :text="displayConclusion"
      copyable
      collapsible
      empty-text="暂无分析结论。可从数据集一键生成看板后查看。"
    >
      <template #actions>
        <el-button link type="primary" :loading="reanalyzing" @click="reanalyze">重新 AI 分析</el-button>
      </template>
    </ConclusionPanel>

    <section class="board-head">
      <div>
        <h3>图表布局</h3>
        <p v-if="editing">编辑模式：拖拽卡片调整位置，右下角拉伸尺寸。点击柱/扇区可联动过滤。</p>
        <p v-else>预览模式：布局已锁定。点击图表维度，全部图表按同一条件过滤。</p>
      </div>
      <span class="drag-hint" :class="{ locked: !editing }">
        <el-icon><Rank /></el-icon>
        {{ editing ? "可拖拽" : "布局已锁定" }}
      </span>
    </section>

    <div ref="boardRef" class="board" :class="{ preview: !editing }" v-loading="filtering">
      <el-empty v-if="!chartCount" description="看板暂无图表，请返回列表新建或从数据集一键生成。" />
      <GridLayout
        v-else
        v-model:layout="layout"
        :col-num="12"
        :row-height="30"
        :is-draggable="editing"
        :is-resizable="editing"
      >
        <GridItem v-for="item in layout" :key="item.i" :x="item.x" :y="item.y" :w="item.w" :h="item.h" :i="item.i">
          <el-card class="tile" shadow="never" v-loading="refreshingId === item.chart_id">
            <div class="tile-head">
              <span v-if="editing" class="grip" aria-hidden="true">
                <el-icon><Rank /></el-icon>
              </span>
              <strong>{{ chartMap[item.chart_id]?.title || "图表" }}</strong>
              <div class="tile-ops">
                <el-tag size="small" type="info" effect="plain">{{ typeLabel(chartMap[item.chart_id]?.chart_type) }}</el-tag>
                <el-tooltip content="下载图片" placement="top">
                  <el-button circle size="small" @click.stop="downloadTile(item.chart_id)">
                    <el-icon><Download /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="AI 解读该图表" placement="top">
                  <el-button circle size="small" @click.stop="interpretChart(item.chart_id)">
                    <el-icon><ChatDotRound /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="刷新" placement="top">
                  <el-button circle size="small" @click.stop="refreshChart(item.chart_id)">
                    <el-icon><Refresh /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
            <ChartPanel
              v-if="chartReady(item.chart_id)"
              :data-chart-id="String(item.chart_id)"
              lazy
              :option="chartMap[item.chart_id].option"
              @click="onChartClick(chartMap[item.chart_id], $event)"
            />
            <el-empty
              v-else-if="failedIds.has(item.chart_id) || !chartMap[item.chart_id]"
              class="tile-empty"
              description="图表渲染失败，请点击刷新重试"
            />
            <el-empty v-else class="tile-empty" description="暂无数据" />
          </el-card>
        </GridItem>
      </GridLayout>
    </div>

    <el-dialog v-model="interpretVisible" title="AI 解读" width="520px">
      <p class="interpret-body">{{ interpretText }}</p>
      <template #footer>
        <el-button type="primary" @click="interpretVisible = false">知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { onBeforeRouteLeave, useRouter, useRoute } from "vue-router";
import { Back, ChatDotRound, Coin, DataAnalysis, Document, Download, Location, Rank, Refresh, TrendCharts } from "@element-plus/icons-vue";
import { ElLoading, ElMessageBox } from "element-plus";
import { GridItem, GridLayout } from "grid-layout-plus";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import { aiApi, chartApi, dashboardApi, type ChartItem, type DashboardItem, type LayoutItem } from "../api";
import ChartPanel from "../components/ChartPanel.vue";
import ConclusionPanel from "../components/ConclusionPanel.vue";
import { toastError, toastSuccess } from "../utils/notify";

const MOCK_REGIONS = ["华南", "华东", "华北", "西南"];

const route = useRoute();
const router = useRouter();
const dashboard = ref<DashboardItem>();
const charts = ref<ChartItem[]>([]);
const layout = ref<LayoutItem[]>([]);
const filterField = ref("");
const filterValue = ref("");
const region = ref("");
const dateRange = ref<[string, string] | null>(null);
const mode = ref<"preview" | "edit">("preview");
const boardRef = ref<HTMLElement>();
const loading = ref(false);
const filtering = ref(false);
const saving = ref(false);
const refreshingId = ref<number | null>(null);
const reanalyzing = ref(false);
const interpretVisible = ref(false);
const interpretText = ref("");
const conclusionOverride = ref("");
const savedLayoutJson = ref("[]");
const failedIds = ref<Set<number>>(new Set());

const editing = computed(() => mode.value === "edit");
const chartMap = computed(() => Object.fromEntries(displayCharts.value.map((item) => [item.id, item])));
const chartCount = computed(() => dashboard.value?.chart_ids?.length || layout.value.length);
const layoutDirty = computed(() => editing.value && JSON.stringify(layout.value) !== savedLayoutJson.value);
const regionField = computed(() => {
  const hit = boardCharts.value.find((item) => /区域|region/i.test(item.x_field));
  return hit?.x_field || "区域";
});
const boardCharts = computed(() => {
  const ids = new Set(layout.value.map((item) => item.chart_id));
  return charts.value.filter((item) => ids.has(item.id));
});
const regionOptions = computed(() => {
  const chart = boardCharts.value.find((item) => item.x_field === regionField.value);
  const cats = extractCategories(chart?.option);
  return cats.length ? cats : MOCK_REGIONS;
});
const displayCharts = computed(() =>
  charts.value.map((item) => ({ ...item, option: compactChartOption(applyDateFilter(item.option)) })),
);
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
    items.push({ label: chart.title, value: Number(nums.reduce((a, b) => a + b, 0).toFixed(2)), hint: "当前视图合计" });
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
const displayConclusion = computed(() => conclusionOverride.value || boardConclusion.value);
const activeTags = computed(() => {
  const tags: { key: string; label: string }[] = [];
  if (dateRange.value) tags.push({ key: "date", label: `时间：${dateRange.value[0]} ~ ${dateRange.value[1]}` });
  if (region.value) tags.push({ key: "region", label: `区域：${region.value}` });
  if (filterValue.value && filterField.value !== regionField.value) {
    tags.push({ key: "dim", label: `${filterField.value}：${filterValue.value}` });
  }
  return tags;
});

function snapshotLayout() {
  savedLayoutJson.value = JSON.stringify(layout.value);
}

function kpiTip(item: { label: string; hint?: string }) {
  if (/行数/.test(item.label)) return "当前看板关联数据集的总行数";
  if (/合计|求和/.test(item.label)) return item.hint || "该指标在全表上的合计值";
  if (/均值|平均/.test(item.label)) return item.hint || "该指标在全表上的平均值";
  if (/主导/.test(item.label)) return item.hint || "出现次数最多的分类值";
  if (/图表/.test(item.label)) return "当前看板已挂载的图表数量";
  return item.hint || "基于当前看板数据计算";
}

function kpiIcon(label: string) {
  if (/行数/.test(label)) return Document;
  if (/合计|求和/.test(label)) return Coin;
  if (/均值|平均/.test(label)) return TrendCharts;
  if (/主导/.test(label)) return Location;
  return DataAnalysis;
}

function kpiTone(label: string) {
  if (/行数/.test(label)) return "tone-blue";
  if (/合计|求和/.test(label)) return "tone-navy";
  if (/均值|平均/.test(label)) return "tone-sky";
  return "tone-slate";
}

function formatKpi(value: string | number) {
  if (typeof value === "string" && /[^\d.\-]/.test(value)) return value;
  const num = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(num)) return String(value);
  if (Math.abs(num) >= 10000) return `${(num / 10000).toFixed(2)} 万`;
  return num.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function typeLabel(type?: string) {
  return ({ bar: "柱状对比", line: "趋势", pie: "结构占比", scatter: "相关分析" } as Record<string, string>)[type || ""] || "图表";
}

function extractCategories(option?: Record<string, unknown>) {
  if (!option) return [] as string[];
  const axis = option.xAxis as { data?: string[] } | undefined;
  if (Array.isArray(axis?.data) && axis.data.length) return axis.data.map(String);
  const series = (option.series as any[])?.[0];
  if (Array.isArray(series?.data) && series.data[0]?.name) return series.data.map((row: any) => String(row.name));
  return [];
}

const CHART_PALETTE = ["#2563eb", "#0ea5e9", "#10b981", "#f59e0b", "#8b5cf6", "#f43f5e", "#14b8a6", "#eab308", "#6366f1", "#fb7185"];

function compactChartOption(option: Record<string, unknown>) {
  if (!option) return option;
  const cloned = JSON.parse(JSON.stringify(option)) as Record<string, unknown>;
  cloned.title = { show: false };
  cloned.grid = { left: 12, right: 48, top: 24, bottom: 44, containLabel: true };
  const cats = extractCategories(cloned);
  const seriesList = (cloned.series as any[]) || [];
  const isPie = seriesList.some((series) => series?.type === "pie");
  const legendData: string[] = [];
  if (isPie) {
    cloned.color = CHART_PALETTE;
    for (const series of seriesList) {
      if (series?.type !== "pie" || !Array.isArray(series.data)) continue;
      series.data = series.data.map((row: any, index: number) => {
        const item = typeof row === "object" && row ? { ...row } : { value: row };
        legendData.push(String(item.name ?? ""));
        item.itemStyle = { ...(item.itemStyle || {}), color: CHART_PALETTE[index % CHART_PALETTE.length] };
        return item;
      });
    }
  } else {
    for (const series of seriesList) {
      if (series?.name) legendData.push(String(series.name));
    }
  }
  cloned.legend = {
    show: true,
    bottom: 0,
    left: "center",
    itemGap: 20,
    textStyle: { width: 80, overflow: "none" },
    ...(legendData.length ? { data: legendData } : {}),
  };
  for (const series of seriesList) {
    if (series?.type === "bar" && cats.length && cats.length <= 8) {
      series.barMaxWidth = 56;
      series.barCategoryGap = "36%";
    }
  }
  if (cloned.xAxis && typeof cloned.xAxis === "object" && !Array.isArray(cloned.xAxis)) {
    cloned.xAxis = {
      ...(cloned.xAxis as object),
      nameLocation: "end",
      nameGap: 12,
      axisLabel: {
        interval: 0,
        hideOverlap: true,
        width: 100,
        overflow: "none",
      },
    };
  }
  if (cloned.yAxis && typeof cloned.yAxis === "object" && !Array.isArray(cloned.yAxis)) {
    cloned.yAxis = { ...(cloned.yAxis as object), name: "", nameGap: 12, nameLocation: "middle" };
  }
  return cloned;
}

function parseLooseDate(raw: string) {
  const text = String(raw).trim().replace(/\./g, "/");
  const iso = Date.parse(text.includes("T") ? text : text.replace(/年|月/g, "-").replace(/日/g, ""));
  if (!Number.isNaN(iso)) return iso;
  const m = text.match(/(\d{4})[/-](\d{1,2})[/-](\d{1,2})/);
  if (m) return Date.parse(`${m[1]}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}`);
  return Number.NaN;
}

function applyDateFilter(option: Record<string, unknown>) {
  if (!dateRange.value || !option) return option;
  const start = Date.parse(dateRange.value[0]);
  const end = Date.parse(dateRange.value[1]) + 86400000 - 1;
  const cloned = JSON.parse(JSON.stringify(option)) as Record<string, unknown>;
  const axis = cloned.xAxis as { data?: string[] } | undefined;
  const seriesList = (cloned.series as any[]) || [];
  if (Array.isArray(axis?.data) && axis.data.length) {
    const keep = axis.data.map((name) => {
      const ts = parseLooseDate(String(name));
      return Number.isNaN(ts) ? true : ts >= start && ts <= end;
    });
    if (keep.every(Boolean)) return option;
    axis.data = axis.data.filter((_, index) => keep[index]);
    for (const series of seriesList) {
      if (Array.isArray(series.data)) series.data = series.data.filter((_: unknown, index: number) => keep[index]);
    }
    return cloned;
  }
  for (const series of seriesList) {
    if (!Array.isArray(series.data) || !series.data[0]?.name) continue;
    const filtered = series.data.filter((row: any) => {
      const ts = parseLooseDate(String(row.name));
      return Number.isNaN(ts) ? true : ts >= start && ts <= end;
    });
    if (filtered.length !== series.data.length) series.data = filtered;
  }
  return cloned;
}

function hasSeries(option?: Record<string, unknown>) {
  const series = option?.series as any[] | undefined;
  if (!Array.isArray(series) || !series.length) return false;
  return series.some((item) => Array.isArray(item?.data) && item.data.length);
}

function chartReady(id: number) {
  return !failedIds.value.has(id) && hasSeries(chartMap.value[id]?.option);
}

async function loadCharts() {
  filtering.value = true;
  try {
    const filter = filterField.value ? { field: filterField.value, value: filterValue.value } : undefined;
    const { data } = await chartApi.list(filter);
    charts.value = data;
    failedIds.value = new Set();
  } catch {
    toastError("图表加载失败");
    failedIds.value = new Set(layout.value.map((item) => item.chart_id));
  } finally {
    filtering.value = false;
  }
}

async function load() {
  loading.value = true;
  try {
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
    snapshotLayout();
    await loadCharts();
  } catch (error: any) {
    toastError(error.response?.data?.detail || "看板加载失败");
  } finally {
    loading.value = false;
  }
}

async function onChartClick(chart: ChartItem, payload: { name: string }) {
  filterField.value = chart.x_field;
  filterValue.value = payload.name;
  if (chart.x_field === regionField.value) region.value = payload.name;
  await loadCharts();
}

function clearTag(key: string) {
  if (key === "date") dateRange.value = null;
  if (key === "region") {
    region.value = "";
    if (filterField.value === regionField.value) {
      filterField.value = "";
      filterValue.value = "";
      loadCharts();
    }
  }
  if (key === "dim") {
    filterField.value = "";
    filterValue.value = "";
    loadCharts();
  }
}

function clearAllFilters() {
  dateRange.value = null;
  region.value = "";
  filterField.value = "";
  filterValue.value = "";
  loadCharts();
}

async function saveLayout() {
  if (!dashboard.value) return;
  saving.value = true;
  try {
    await dashboardApi.update(dashboard.value.id, { layout: layout.value, chart_ids: dashboard.value.chart_ids });
    snapshotLayout();
    toastSuccess("布局已保存");
  } catch (error: any) {
    toastError(error.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function share() {
  if (!dashboard.value) return;
  const overlay = ElLoading.service({ lock: true, text: "正在生成分享链接…", background: "rgba(15, 23, 42, 0.35)" });
  try {
    const { data } = await dashboardApi.share(dashboard.value.id);
    const url = `${window.location.origin}${data.path}`;
    await navigator.clipboard.writeText(url);
    toastSuccess("分享链接已复制");
  } catch (error: any) {
    toastError(error.response?.data?.detail || "生成分享链接失败");
  } finally {
    overlay.close();
  }
}

async function exportPdf() {
  if (!boardRef.value) return;
  const overlay = ElLoading.service({ lock: true, text: "正在导出 PDF…", background: "rgba(15, 23, 42, 0.35)" });
  try {
    const canvas = await html2canvas(boardRef.value, { scale: 1.2 });
    const img = canvas.toDataURL("image/png");
    const pdf = new jsPDF("l", "pt", "a4");
    const width = pdf.internal.pageSize.getWidth();
    const height = (canvas.height * width) / canvas.width;
    pdf.addImage(img, "PNG", 0, 0, width, height);
    pdf.save(`${dashboard.value?.title || "dashboard"}.pdf`);
    toastSuccess("PDF 已导出");
  } catch {
    toastError("导出失败");
  } finally {
    overlay.close();
  }
}

async function refreshChart(id: number) {
  refreshingId.value = id;
  try {
    const filter = filterField.value ? { field: filterField.value, value: filterValue.value } : undefined;
    const { data } = await chartApi.get(id, filter);
    charts.value = charts.value.map((item) => (item.id === id ? data : item));
    const next = new Set(failedIds.value);
    next.delete(id);
    failedIds.value = next;
    toastSuccess("图表已刷新");
  } catch {
    const next = new Set(failedIds.value);
    next.add(id);
    failedIds.value = next;
    toastError("图表刷新失败");
  } finally {
    refreshingId.value = null;
  }
}

async function downloadTile(id: number) {
  const wrap = boardRef.value?.querySelector(`[data-chart-id="${id}"]`) as HTMLElement | null;
  const tile = wrap?.closest(".tile") as HTMLElement | null;
  if (!tile) {
    toastError("未找到图表");
    return;
  }
  try {
    const canvas = await html2canvas(tile);
    const link = document.createElement("a");
    link.download = `${chartMap.value[id]?.title || "chart"}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  } catch {
    toastError("下载失败");
  }
}

async function interpretChart(id: number) {
  const chart = charts.value.find((item) => item.id === id);
  if (!chart) return;
  const overlay = ElLoading.service({ lock: true, text: "正在解读图表…", background: "rgba(15, 23, 42, 0.35)" });
  try {
    const { data } = await aiApi.chat({
      dataset_id: chart.dataset_id,
      message: `请解读图表「${chart.title}」，按${chart.x_field}分析${chart.y_field || "指标"}。`,
      title: chart.title,
      chart_type: chart.chart_type,
      x_field: chart.x_field,
      y_field: chart.y_field,
      aggregation: chart.aggregation,
      save: false,
    });
    interpretText.value = data.reply || data.conclusion || data.insight || chart.insight || "暂无解读";
    interpretVisible.value = true;
  } catch (error: any) {
    interpretText.value = chart.insight || error.response?.data?.detail || "解读失败，已回退到图表原有结论。";
    interpretVisible.value = true;
  } finally {
    overlay.close();
  }
}

async function reanalyze() {
  const datasetId = boardCharts.value[0]?.dataset_id || charts.value[0]?.dataset_id;
  if (!datasetId) {
    toastError("当前看板没有可分析的数据集");
    return;
  }
  reanalyzing.value = true;
  try {
    const { data } = await aiApi.recommend(datasetId);
    conclusionOverride.value = data.conclusion || "";
    toastSuccess("分析结论已更新");
  } catch (error: any) {
    toastError(error.response?.data?.detail || "重新分析失败");
  } finally {
    reanalyzing.value = false;
  }
}

async function confirmLeave(): Promise<boolean> {
  if (!layoutDirty.value) return true;
  try {
    await ElMessageBox.confirm("布局尚未保存，确定离开吗？", "未保存确认", {
      type: "warning",
      confirmButtonText: "离开",
      cancelButtonText: "继续编辑",
    });
    return true;
  } catch {
    return false;
  }
}

async function goBack() {
  if (await confirmLeave()) router.push("/dashboards");
}

watch(region, (value, previous) => {
  if (value === previous) return;
  if (value && filterField.value === regionField.value && filterValue.value === value) return;
  if (!value) {
    if (filterField.value === regionField.value) {
      filterField.value = "";
      filterValue.value = "";
      loadCharts();
    }
    return;
  }
  filterField.value = regionField.value;
  filterValue.value = value;
  loadCharts();
});

watch(mode, async (next, prev) => {
  if (prev === "edit" && next === "preview" && JSON.stringify(layout.value) !== savedLayoutJson.value) {
    try {
      await ElMessageBox.confirm("布局尚未保存，切换到预览将保留未保存改动但无法拖拽。是否继续？", "未保存确认", {
        type: "warning",
        confirmButtonText: "继续预览",
        cancelButtonText: "返回编辑",
      });
    } catch {
      mode.value = "edit";
    }
  }
});

onBeforeRouteLeave(async () => confirmLeave());

onMounted(load);
</script>

<style scoped>
.dash {
  padding-bottom: 32px;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
  margin-bottom: 12px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid #e2e8f0;
  box-shadow: var(--card-shadow);
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex-wrap: wrap;
}
.titles h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.3;
}
.kicker {
  margin: 0 0 2px;
  font-size: 12px;
  letter-spacing: 0.6px;
  color: #2563eb;
  font-weight: 600;
}
.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  padding: 10px 14px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: var(--card-shadow);
}
.filter-fields {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.filter-label {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}
.filter-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
.kpi {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: var(--card-shadow);
  cursor: help;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.kpi:hover {
  transform: translateY(-2px);
  box-shadow: var(--card-shadow-hover);
}
.kpi-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.tone-blue { background: #2563eb; }
.tone-navy { background: #1e3a8a; }
.tone-sky { background: #0ea5e9; }
.tone-slate { background: #334155; }
.kpi-body { min-width: 0; }
.kpi-label,
.kpi small {
  display: block;
  color: #64748b;
  font-size: 12px;
}
.kpi strong {
  display: block;
  margin: 4px 0 2px;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.02em;
}
.board-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
  margin: 16px 0 10px;
}
.board-head h3 {
  margin: 0 0 4px;
  font-size: 15px;
  color: #0f172a;
}
.board-head p {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}
.drag-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
  white-space: nowrap;
}
.drag-hint.locked {
  color: #64748b;
}
.board {
  background: #eef2f7;
  min-height: 480px;
  padding: 10px;
  border-radius: 14px;
  border: 1px dashed #cbd5e1;
}
.board.preview {
  border-style: solid;
  border-color: #e2e8f0;
}
.tile {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  box-shadow: var(--card-shadow);
  position: relative;
  transition: box-shadow 0.15s ease;
}
.tile :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 10px 12px 8px;
  box-sizing: border-box;
}
.tile:hover {
  box-shadow: var(--card-shadow-hover);
}
.tile-ops {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 10px;
  margin-left: 16px;
}
.tile-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.tile-head strong {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.grip {
  color: #94a3b8;
  cursor: grab;
  display: inline-flex;
}
.tile-empty {
  flex: 1;
  padding: 24px 0;
}
.interpret-body {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.7;
  color: #334155;
}
.tile :deep(.chart-wrap) {
  flex: 1;
  min-height: 280px;
  height: auto;
}
.tile :deep(.chart-box) {
  min-height: 280px;
}
:deep(.vgl-item) {
  box-sizing: border-box;
}
:deep(.vgl-item-resizing),
:deep(.vgl-item-dragging) {
  z-index: 20;
}
@media (max-width: 1100px) {
  .kpis {
    grid-template-columns: repeat(2, 1fr);
  }
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
