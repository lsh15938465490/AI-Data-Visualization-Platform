<template>
  <div class="studio-page" v-loading="pageLoading || loadingMeta" element-loading-text="正在加载默认数据…">
  <div class="page-header">
    <h2>图表工作室</h2>
  </div>
  <el-row :gutter="20">
    <el-col :span="8">
      <el-card class="config-card">
        <el-form label-position="top" class="studio-form">
          <p class="group-title">数据集</p>
          <el-form-item label="数据集">
            <el-select v-model="datasetId" placeholder="选择数据集" style="width: 100%" :loading="loadingMeta">
              <el-option v-for="item in datasets" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-divider />
          <p class="group-title">图表设置</p>
          <el-form-item label="标题">
            <el-input v-model="title" />
          </el-form-item>
          <el-form-item label="图表类型">
            <el-select v-model="chartType" style="width: 100%">
              <el-option label="柱状图" value="bar" />
              <el-option label="折线图" value="line" />
              <el-option label="饼图" value="pie" />
              <el-option label="散点图" value="scatter" />
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
          <el-divider />
          <p class="group-title">聚合设置</p>
          <el-form-item label="聚合">
            <el-select v-model="aggregation" style="width: 100%">
              <el-option label="求和" value="sum" />
              <el-option label="平均" value="mean" />
              <el-option label="计数" value="count" />
              <el-option label="最大" value="max" />
              <el-option label="最小" value="min" />
            </el-select>
          </el-form-item>
          <div class="form-actions">
            <el-button @click="resetForm">重置</el-button>
            <el-button :disabled="!canBuild" :loading="previewing" @click="previewChart">预览</el-button>
            <el-button type="primary" :disabled="!canBuild" :loading="saving" @click="createChart(true)">生成并保存</el-button>
          </div>
        </el-form>
        <el-divider>智能推荐</el-divider>
        <p class="hint">先分析字段类型、空值与分布，再给出图表建议（配置了大模型时会走 API）。</p>
        <el-space wrap>
          <el-tag v-for="item in recommendations" :key="item.reason" class="rec" @click="applyRec(item)">
            {{ item.title || item.reason }}
          </el-tag>
        </el-space>
        <el-divider>对话式分析</el-divider>
        <div class="chat-log" ref="chatLogRef">
          <p v-for="(msg, index) in messages" :key="index" :class="msg.role">{{ msg.text }}</p>
          <ThinkingIndicator v-if="thinking" />
        </div>
        <el-input
          class="hint-textarea"
          :class="{ 'is-empty': !question.trim() }"
          v-model="question"
          type="textarea"
          :rows="3"
          :placeholder="questionHint"
        />
        <el-button style="margin-top: 8px" type="success" :disabled="!datasetId" :loading="aiLoading" @click="chat">发送</el-button>
      </el-card>
    </el-col>
    <el-col :span="16">
      <el-card v-loading="previewing || saving || aiLoading">
        <div class="preview" ref="previewRef">
          <ChartPanel v-if="option && Object.keys(option).length" :option="option" />
          <el-empty v-else description="请选择 X 维度、Y 指标生成图表" />
        </div>
        <div class="chart-ops">
          <el-button :disabled="!option" @click="exportPng">导出图表</el-button>
        </div>
        <ConclusionPanel
          :text="conclusion || insight"
          :source="recSource"
          copyable
          collapsible
          empty-text="选择维度并预览或生成后，这里会输出分析结论。"
        />
        <el-alert v-for="item in anomalies" :key="item.message" :title="item.message" type="warning" show-icon style="margin-top: 8px" />
      </el-card>
    </el-col>
  </el-row>
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
  if (!datasetId.value) return;
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
  min-height: calc(100vh - 88px);
  position: relative;
}
.config-card :deep(.el-form-item) {
  margin-bottom: 14px;
}
.group-title {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 700;
  color: #1e3a8a;
}
.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.preview {
  height: 420px;
}
.chart-ops {
  margin: 12px 0 0;
}
.chat-log {
  max-height: 160px;
  overflow: auto;
  margin-bottom: 8px;
  font-size: 13px;
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
.hint {
  color: #64748b;
  font-size: 12px;
  margin: 0 0 8px;
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
