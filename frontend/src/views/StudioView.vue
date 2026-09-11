<template>
  <div class="studio-page" v-loading="pageLoading || loadingMeta" element-loading-text="正在加载默认数据…">
    <div class="page-header">
      <h2>图表工作室</h2>
    </div>
    <div class="studio-body">
      <el-card class="pane config-card">
        <el-form label-position="left" label-width="72px" class="studio-form" @submit.prevent>
          <el-form-item label="数据集">
            <el-select v-model="datasetId" placeholder="选择数据集" style="width: 100%" :loading="loadingMeta">
              <el-option v-for="item in datasets" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="标题">
            <el-input v-model="title" />
          </el-form-item>
          <div class="form-grid">
            <el-form-item label="图表类型">
              <el-select v-model="chartType" style="width: 100%">
                <el-option label="柱状图" value="bar" />
                <el-option label="折线图" value="line" />
                <el-option label="饼图" value="pie" />
                <el-option label="散点图" value="scatter" />
              </el-select>
            </el-form-item>
            <el-form-item label="聚合">
              <el-select v-model="aggregation" style="width: 100%">
                <el-option label="求和" value="sum" />
                <el-option label="平均" value="mean" />
                <el-option label="计数" value="count" />
                <el-option label="最大" value="max" />
                <el-option label="最小" value="min" />
              </el-select>
            </el-form-item>
            <el-form-item label="维度 X">
              <el-select v-model="xField" style="width: 100%">
                <el-option v-for="col in columns" :key="col" :label="col" :value="col" />
              </el-select>
            </el-form-item>
            <el-form-item label="指标 Y">
              <el-select v-model="yField" placeholder="请选择数值指标" style="width: 100%" clearable>
                <el-option v-for="col in yMetricColumns" :key="col" :label="col" :value="col" />
              </el-select>
            </el-form-item>
          </div>
          <div class="form-actions">
            <el-button @click="resetForm">重置</el-button>
            <el-button :disabled="!canBuild" :loading="previewing" @click="previewChart">预览</el-button>
            <el-button type="primary" :disabled="!canBuild" :loading="saving" @click="createChart(true)">生成并保存</el-button>
          </div>
        </el-form>
        <div class="studio-ai">
          <p class="group-title">智能推荐</p>
          <div class="rec-wrap">
            <el-empty v-if="!recommendations.length" description="选择数据集后显示推荐" :image-size="40" />
            <el-space v-else wrap>
              <el-tag v-for="item in recommendations" :key="item.reason" class="rec" @click="applyRec(item)">
                {{ item.title || item.reason }}
              </el-tag>
            </el-space>
          </div>
          <p class="group-title">对话式分析</p>
          <div class="chat-log" ref="chatLogRef">
            <p v-if="!messages.length && !thinking" class="chat-placeholder">{{ questionHint }}</p>
            <p v-for="(msg, index) in messages" :key="index" :class="msg.role">{{ msg.text }}</p>
            <ThinkingIndicator v-if="thinking" />
          </div>
          <div class="composer">
            <el-input
              class="hint-textarea"
              :class="{ 'is-empty': !question.trim() }"
              v-model="question"
              type="textarea"
              :rows="2"
              :placeholder="questionHint"
              @keydown.enter.exact.prevent="chat"
            />
            <el-button class="send-btn" type="success" :disabled="!datasetId" :loading="aiLoading" @click="chat">发送</el-button>
          </div>
        </div>
      </el-card>
      <el-card class="pane preview-card" v-loading="previewing || saving || aiLoading">
        <div class="preview-wrap">
          <div class="preview" ref="previewRef">
            <ChartPanel v-if="option && Object.keys(option).length" :option="option" />
            <el-empty v-else description="请选择 X 维度、Y 指标生成图表" />
          </div>
        </div>
        <div class="preview-toolbar">
          <el-button :disabled="!option" @click="exportPng">导出图表</el-button>
        </div>
        <div class="preview-meta">
          <ConclusionPanel
            :text="conclusion || insight"
            :source="recSource"
            copyable
            collapsible
            empty-text="选择维度并预览或生成后，这里会输出分析结论。"
          />
          <el-alert
            v-if="anomalies.length"
            :title="anomalies.length === 1 ? anomalies[0].message : `检测到 ${anomalies.length} 条异常（按偏离程度列出）`"
            type="warning"
            show-icon
            class="anomaly-alert"
          >
            <ul v-if="anomalies.length > 1" class="anomaly-list">
              <li v-for="item in anomalies" :key="item.message">{{ item.message }}</li>
            </ul>
          </el-alert>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import html2canvas from "html2canvas";
import { aiApi, chartApi, datasetApi, type Dataset } from "../api";
import ChartPanel from "../components/ChartPanel.vue";
import ConclusionPanel from "../components/ConclusionPanel.vue";
import ThinkingIndicator from "../components/ThinkingIndicator.vue";
import { toastError, toastSuccess } from "../utils/notify";

const route = useRoute();
const datasets = ref<Dataset[]>([]);
const datasetId = ref<number>();
const title = ref("未命名图表");
const chartType = ref("bar");
const xField = ref("");
const yField = ref("");
const aggregation = ref("sum");
const style = ref<Record<string, unknown>>({});
const EXAMPLE_QUESTION = "帮我分析近三个月销售额趋势";
const questionHint = `例如：${EXAMPLE_QUESTION}；把颜色改成橙色；图例放到顶部`;
const question = ref("");
const option = ref<Record<string, unknown> | null>(null);
const insight = ref("");
const conclusion = ref("");
const recSource = ref("");
const aiLoading = ref(false);
const thinking = ref(false);
const pageLoading = ref(true);
const bootstrapping = ref(true);
const loadingMeta = ref(false);
const previewing = ref(false);
const saving = ref(false);
const recommendations = ref<any[]>([]);
const anomalies = ref<any[]>([]);
const messages = ref<{ role: string; text: string }[]>([]);
const previewRef = ref<HTMLElement>();
const chatLogRef = ref<HTMLElement>();
const numericColumns = ref<string[]>([]);
const columns = computed(() => datasets.value.find((d) => d.id === datasetId.value)?.columns || []);
const yMetricColumns = computed(() => {
  if (aggregation.value === "count") return columns.value;
  return numericColumns.value;
});
const canBuild = computed(() => Boolean(datasetId.value && xField.value && yField.value));

watch(yMetricColumns, (cols) => {
  if (!cols.length) {
    yField.value = "";
    return;
  }
  if (!cols.includes(yField.value)) yField.value = cols[0];
});

watch(datasetId, async (id) => {
  if (!id || bootstrapping.value) return;
  await hydrateDataset(id);
});

async function hydrateDataset(id: number) {
  loadingMeta.value = true;
  try {
    const [{ data: preview }, { data: rec }] = await Promise.all([
      datasetApi.preview(id),
      aiApi.recommend(id),
    ]);
    const cols = (preview.columns as string[]) || [];
    const numeric = cols.filter((col) =>
      (preview.rows as Record<string, unknown>[]).some((row) => {
        const value = row[col];
        if (typeof value === "number" && Number.isFinite(value)) return true;
        if (typeof value === "string" && value.trim() && /^-?\d+(\.\d+)?$/.test(value.trim())) return true;
        return false;
      }),
    );
    numericColumns.value = numeric;
    xField.value = cols.find((col) => !numeric.includes(col)) || cols[0] || "";
    yField.value = numeric[0] || "";
    recommendations.value = rec.recommendations || [];
    conclusion.value = rec.conclusion || "";
    recSource.value = rec.source || "";
    option.value = null;
  } catch (error: any) {
    toastError(error.response?.data?.detail || "加载数据集失败");
  } finally {
    loadingMeta.value = false;
  }
}

async function load() {
  pageLoading.value = true;
  bootstrapping.value = true;
  try {
    const { data } = await datasetApi.list();
    datasets.value = data;
    const qid = Number(route.query.datasetId);
    const id = qid || data[0]?.id;
    if (id) {
      datasetId.value = id;
      await hydrateDataset(id);
    }
  } catch (error: any) {
    toastError(error.response?.data?.detail || "加载失败");
  } finally {
    bootstrapping.value = false;
    pageLoading.value = false;
  }
}

function applyRec(item: any) {
  chartType.value = item.chart_type;
  xField.value = item.x_field;
  yField.value = item.y_field;
  aggregation.value = item.aggregation;
  toastSuccess("已应用推荐配置");
}

function resetForm() {
  title.value = "未命名图表";
  chartType.value = "bar";
  aggregation.value = "sum";
  option.value = null;
  insight.value = "";
  const cols = columns.value;
  xField.value = cols.find((col) => !numericColumns.value.includes(col)) || cols[0] || "";
  yField.value = numericColumns.value[0] || "";
  toastSuccess("已重置图表配置");
}

async function createChart(save: boolean) {
  if (!datasetId.value || !xField.value || !yField.value) {
    toastError("请先选择 X 维度和 Y 指标");
    return;
  }
  if (save) saving.value = true;
  else previewing.value = true;
  try {
    const { data } = await chartApi.create({
      title: title.value,
      dataset_id: datasetId.value,
      chart_type: chartType.value,
      x_field: xField.value,
      y_field: yField.value,
      aggregation: aggregation.value,
      save,
    });
    option.value = data.option;
    insight.value = data.insight;
    if (data.insight) conclusion.value = data.insight;
    if (save) toastSuccess("图表已保存");
    else toastSuccess("已生成预览");
  } catch (error: any) {
    toastError(error.response?.data?.detail || "生成失败，请检查字段是否匹配");
  } finally {
    saving.value = false;
    previewing.value = false;
  }
}

function previewChart() {
  return createChart(false);
}

async function scrollChatToBottom() {
  await nextTick();
  const el = chatLogRef.value;
  if (el) el.scrollTop = el.scrollHeight;
}

async function chat() {
  if (!datasetId.value || aiLoading.value) return;
  let text = question.value.trim();
  if (!text || text === EXAMPLE_QUESTION) {
    text = EXAMPLE_QUESTION;
    question.value = "";
  }
  messages.value.push({ role: "user", text });
  thinking.value = true;
  await scrollChatToBottom();
  aiLoading.value = true;
  try {
    const { data } = await aiApi.chat({
      dataset_id: datasetId.value,
      message: text,
      title: title.value,
      chart_type: chartType.value,
      x_field: xField.value,
      y_field: yField.value,
      aggregation: aggregation.value,
      style: style.value,
      save: true,
    });
    option.value = data.option;
    insight.value = data.insight;
    conclusion.value = data.conclusion || data.insight;
    title.value = data.title;
    chartType.value = data.chart_type;
    xField.value = data.x_field;
    yField.value = data.y_field;
    aggregation.value = data.aggregation;
    style.value = data.style || {};
    recommendations.value = data.recommendations || [];
    anomalies.value = data.anomalies || [];
    messages.value.push({ role: "assistant", text: "" });
    const index = messages.value.length - 1;
    const full = data.reply || "";
    const step = Math.max(1, Math.ceil(full.length / 48));
    for (let i = 0; i < full.length; i += step) {
      messages.value[index].text = full.slice(0, i + step);
      await scrollChatToBottom();
      await new Promise((resolve) => setTimeout(resolve, 18));
    }
    messages.value[index].text = full;
    toastSuccess("图表已保存");
    await scrollChatToBottom();
  } catch (error: any) {
    toastError(error.response?.data?.detail || "分析失败");
  } finally {
    thinking.value = false;
    aiLoading.value = false;
    await scrollChatToBottom();
  }
}

async function exportPng() {
  if (!previewRef.value) return;
  const canvas = await html2canvas(previewRef.value);
  const link = document.createElement("a");
  link.download = `${title.value || "chart"}.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

onMounted(load);
</script>

<style scoped>
.studio-page {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}
.studio-page .page-header {
  flex-shrink: 0;
  margin-bottom: 12px;
}
.studio-page .page-header h2 {
  margin: 0;
  font-size: 20px;
  line-height: 1.3;
}
.studio-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(360px, 400px) 1fr;
  gap: 16px;
}
.pane {
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.pane :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  overflow: hidden;
}
.config-card :deep(.el-form-item) {
  margin-bottom: 10px;
}
.config-card :deep(.el-form-item__label) {
  font-size: 13px;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 8px;
}
.form-grid :deep(.el-form-item__label) {
  width: 64px !important;
}
.group-title {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 700;
  color: #1e3a8a;
}
.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 8px;
}
.studio-ai {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-top: 1px solid #e2e8f0;
  padding-top: 10px;
}
.rec-wrap {
  max-height: 72px;
  overflow: auto;
  margin-bottom: 8px;
}
.rec-wrap :deep(.el-empty) {
  padding: 4px 0;
}
.chat-log {
  flex: 1;
  min-height: 72px;
  overflow: auto;
  margin-bottom: 8px;
  font-size: 13px;
}
.chat-placeholder {
  margin: 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}
.composer {
  display: flex;
  align-items: stretch;
  gap: 8px;
}
.hint-textarea {
  flex: 1;
  min-width: 0;
}
.send-btn {
  margin: 0;
  height: auto;
  padding: 0 16px;
}
.preview-card :deep(.conclusion) {
  margin-top: 0;
  padding: 10px 12px;
}
.preview-card :deep(.conclusion .body) {
  max-height: 88px;
}
.preview-card :deep(.conclusion .body.collapsed) {
  max-height: 56px;
}
.preview-wrap {
  position: relative;
  flex: 1 1 auto;
  min-height: 280px;
}
.preview {
  height: 100%;
  min-height: 280px;
}
.preview :deep(.chart-wrap),
.preview :deep(.el-empty) {
  height: 100%;
  min-height: 280px;
}
.preview :deep(.chart-box) {
  min-height: 280px;
}
.preview-toolbar {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  padding: 8px 0 0;
}
.preview-meta {
  flex: 0 1 34%;
  min-height: 0;
  max-height: 34%;
  overflow: auto;
  margin-top: 8px;
}
.anomaly-alert {
  margin-top: 8px;
}
.anomaly-list {
  margin: 6px 0 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.6;
}
.user {
  color: #2563eb;
}
.assistant {
  color: #334155;
}
.rec {
  cursor: pointer;
}
.hint-textarea :deep(.el-textarea__inner::placeholder) {
  color: #94a3b8 !important;
  -webkit-text-fill-color: #94a3b8;
  opacity: 1;
}
.hint-textarea.is-empty :deep(.el-textarea__inner) {
  color: #94a3b8;
  -webkit-text-fill-color: #94a3b8;
}
.hint-textarea:not(.is-empty) :deep(.el-textarea__inner) {
  color: #0f172a;
  -webkit-text-fill-color: #0f172a;
}
</style>
