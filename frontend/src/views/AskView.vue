<template>
  <div class="page-header">
    <h2>AI 自然语言问答</h2>
    <el-select v-model="datasetId" placeholder="选择数据集" style="width: 280px" :loading="switching">
      <el-option v-for="item in datasets" :key="item.id" :label="item.name" :value="item.id" />
    </el-select>
  </div>
  <el-row :gutter="20" class="ask-layout">
    <el-col :span="9">
      <el-card class="ask-card pane">
        <p class="lead">用自然语言提问，系统会先识别数据特征，再出图并给出分析结论。</p>
        <div class="chips">
          <button
            v-for="item in suggestions"
            :key="item"
            type="button"
            class="chip"
            :class="{ active: question === item }"
            @click="fillChip(item)"
          >
            {{ item }}
          </button>
        </div>
        <div class="chat-log" ref="chatLogRef">
          <p v-for="(msg, index) in messages" :key="index" :class="msg.role">{{ msg.text }}</p>
          <ThinkingIndicator v-if="thinking" />
        </div>
        <div class="composer">
          <el-input
            class="hint-textarea"
            :class="{ 'is-empty': !question.trim() }"
            v-model="question"
            type="textarea"
            :rows="3"
            :placeholder="questionHint"
          />
          <p class="input-tip">输入自然语言，例如：帮我分析近三个月销售额趋势</p>
          <div class="ask-actions">
            <el-checkbox v-model="saveChart">同时保存图表</el-checkbox>
            <el-button type="primary" :disabled="!datasetId" :loading="loading" @click="ask()">提问</el-button>
          </div>
        </div>
      </el-card>
    </el-col>
    <el-col :span="15">
      <el-card class="pane pane-right" v-loading="switching || loading">
        <div class="kpis" v-if="kpis.length">
          <el-tooltip v-for="item in kpis" :key="item.label" :content="kpiTip(item)" placement="top">
            <div class="kpi">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <small>{{ item.hint }}</small>
            </div>
          </el-tooltip>
        </div>
        <div class="preview" ref="previewRef">
          <ChartPanel v-if="option && Object.keys(option).length" :option="option" />
          <el-empty v-else-if="!thinking" description="选择数据集并提问后，这里展示图表" />
          <div v-if="thinking" class="preview-wait" :class="{ overlay: !!(option && Object.keys(option).length) }">
            <ThinkingIndicator />
            <span>正在分析数据并生成图表</span>
          </div>
        </div>
        <div class="chart-ops">
          <el-button :disabled="!option" @click="exportPng">下载图片</el-button>
          <el-button :disabled="!option || savingStudio" :loading="savingStudio" @click="saveToStudio">保存到图表工作室</el-button>
          <el-button :disabled="!conclusion" @click="copyReport">复制分析报告</el-button>
        </div>
        <ConclusionPanel :text="typedConclusion" :source="source" copyable collapsible />
        <el-alert
          v-if="anomalies.length"
          :title="anomalies.length === 1 ? anomalies[0].message : `检测到 ${anomalies.length} 条异常（按偏离程度列出）`"
          type="warning"
          show-icon
          style="margin-top: 8px"
        >
          <ul v-if="anomalies.length > 1" class="anomaly-list">
            <li v-for="item in anomalies" :key="item.message">{{ item.message }}</li>
          </ul>
        </el-alert>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import html2canvas from "html2canvas";
import { aiApi, chartApi, datasetApi, type Dataset } from "../api";
import ChartPanel from "../components/ChartPanel.vue";
import ConclusionPanel from "../components/ConclusionPanel.vue";
import ThinkingIndicator from "../components/ThinkingIndicator.vue";
import { toastError, toastSuccess } from "../utils/notify";

const route = useRoute();
const router = useRouter();
const datasets = ref<Dataset[]>([]);
const datasetId = ref<number>();
const EXAMPLE_QUESTION = "哪个地区销售额最高？近几个月趋势如何？";
const questionHint = `例如：${EXAMPLE_QUESTION}`;
const question = ref("");
const saveChart = ref(false);
const loading = ref(false);
const switching = ref(false);
const thinking = ref(false);
const savingStudio = ref(false);
let askSeq = 0;
const option = ref<Record<string, unknown> | null>(null);
const conclusion = ref("");
const typedConclusion = ref("");
const source = ref("");
const kpis = ref<{ label: string; value: string | number; hint?: string }[]>([]);
const anomalies = ref<any[]>([]);
const messages = ref<{ role: string; text: string }[]>([]);
const chatLogRef = ref<HTMLElement>();
const previewRef = ref<HTMLElement>();
const lastSpec = ref<Record<string, unknown> | null>(null);
const columns = computed(() => datasets.value.find((d) => d.id === datasetId.value)?.columns || []);
const suggestions = computed(() => {
  const cols = columns.value;
  if (!cols.length) return ["帮我概括这份数据的主要特征", "对比各分类指标高低", "看看时间趋势"];
  const metric = cols.find((col) => /销售|额|量|cost|sales|revenue|click/i.test(col)) || cols[cols.length - 1];
  const dim = cols.find((col) => /地区|区域|平台|产品|channel|region|platform/i.test(col)) || cols[0];
  return [`${dim} 的 ${metric} 谁最高？`, `${metric} 最近趋势怎么样？`, `${dim} 占比如何？`];
});

function kpiTip(item: { label: string; hint?: string }) {
  if (/行数/.test(item.label)) return "当前选中数据集总行数";
  if (/合计|求和/.test(item.label)) return item.hint || "该指标在全表上的合计值";
  if (/均值|平均/.test(item.label)) return item.hint || "该指标在全表上的平均值";
  if (/主导/.test(item.label)) return item.hint || "出现次数最多的分类值";
  return item.hint || "基于当前选中数据集计算";
}

function fillChip(item: string) {
  question.value = item;
}

watch(datasetId, async (id) => {
  if (!id) return;
  switching.value = true;
  try {
    const { data } = await aiApi.recommend(id);
    kpis.value = data.kpis || data.features?.kpis || [];
    conclusion.value = data.conclusion || "";
    typedConclusion.value = data.conclusion || "";
    source.value = data.source || "rules";
    option.value = null;
    lastSpec.value = null;
  } catch (error: any) {
    toastError(error.response?.data?.detail || "加载数据集特征失败");
  } finally {
    switching.value = false;
  }
});

async function load() {
  const { data } = await datasetApi.list();
  datasets.value = data;
  const qid = Number(route.query.datasetId);
  if (qid) datasetId.value = qid;
  else if (data[0]) datasetId.value = data[0].id;
}

async function scrollChatToBottom() {
  await nextTick();
  const el = chatLogRef.value;
  if (el) el.scrollTop = el.scrollHeight;
}

async function typeText(full: string, seq: number, onChunk: (text: string) => void) {
  const step = Math.max(1, Math.ceil(full.length / 56));
  for (let i = 0; i < full.length; i += step) {
    if (seq !== askSeq) return;
    onChunk(full.slice(0, i + step));
    await scrollChatToBottom();
    await new Promise((resolve) => setTimeout(resolve, 18));
  }
  if (seq === askSeq) onChunk(full);
}

async function typeReply(full: string, seq: number) {
  messages.value.push({ role: "assistant", text: "" });
  const index = messages.value.length - 1;
  await typeText(full, seq, (text) => {
    messages.value[index].text = text;
  });
}

async function ask(preset?: string) {
  if (!datasetId.value || loading.value) return;
  const typed = question.value.trim();
  const text = (preset || typed || EXAMPLE_QUESTION).trim();
  if (preset) question.value = preset;
  else if (!typed || typed === EXAMPLE_QUESTION) question.value = "";
  const seq = ++askSeq;
  messages.value.push({ role: "user", text });
  thinking.value = true;
  loading.value = true;
  typedConclusion.value = "";
  await scrollChatToBottom();
  try {
    const started = Date.now();
    const { data } = await aiApi.analyze({
      dataset_id: datasetId.value,
      question: text,
      save: saveChart.value,
    });
    if (seq !== askSeq) return;
    const remain = 700 - (Date.now() - started);
    if (remain > 0) await new Promise((resolve) => setTimeout(resolve, remain));
    if (seq !== askSeq) return;
    thinking.value = false;
    option.value = data.option;
    conclusion.value = data.conclusion || data.insight || "";
    source.value = data.source || source.value;
    kpis.value = data.features?.kpis || kpis.value;
    anomalies.value = data.anomalies || [];
    lastSpec.value = {
      title: data.title || text,
      dataset_id: datasetId.value,
      chart_type: data.chart_type,
      x_field: data.x_field,
      y_field: data.y_field,
      aggregation: data.aggregation || "sum",
    };
    await Promise.all([
      typeReply(data.conclusion || data.insight || "已完成分析", seq),
      typeText(conclusion.value, seq, (chunk) => {
        typedConclusion.value = chunk;
      }),
    ]);
    if (data.chart?.id) toastSuccess("图表已保存，可加入仪表盘");
    await scrollChatToBottom();
  } catch (error: any) {
    if (seq === askSeq) toastError(error.response?.data?.detail || "AI 解析失败，请换个问法或检查字段");
  } finally {
    if (seq === askSeq) {
      thinking.value = false;
      loading.value = false;
    }
    await scrollChatToBottom();
  }
}

async function exportPng() {
  if (!previewRef.value || !option.value) return;
  const canvas = await html2canvas(previewRef.value);
  const link = document.createElement("a");
  link.download = "ask-chart.png";
  link.href = canvas.toDataURL("image/png");
  link.click();
}

async function saveToStudio() {
  if (!lastSpec.value || !datasetId.value) {
    toastError("请先生成图表");
    return;
  }
  savingStudio.value = true;
  try {
    await chartApi.create({ ...lastSpec.value, save: true });
    toastSuccess("已保存到图表工作室");
    router.push({ path: "/studio", query: { datasetId: String(datasetId.value) } });
  } catch (error: any) {
    toastError(error.response?.data?.detail || "保存失败，请检查字段是否匹配");
  } finally {
    savingStudio.value = false;
  }
}

async function copyReport() {
  try {
    await navigator.clipboard.writeText(conclusion.value);
    toastSuccess("分析报告已复制");
  } catch {
    toastError("复制失败");
  }
}

onMounted(load);
</script>

<style scoped>
.ask-layout {
  align-items: stretch;
}
.pane {
  box-shadow: var(--card-shadow) !important;
  border: 1px solid #e2e8f0;
}
.pane-right {
  min-height: calc(100vh - 132px);
  border-left: 1px solid #dbe4f0;
}
.lead {
  margin-top: 0;
  color: #475569;
  font-size: 13px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.chip {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.chip:hover {
  background: #dbeafe;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.16);
}
.chip.active {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}
.ask-card {
  height: calc(100vh - 132px);
  display: flex;
  flex-direction: column;
}
.ask-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.chat-log {
  flex: 1;
  min-height: 80px;
  overflow: auto;
  margin-bottom: 8px;
  font-size: 13px;
}
.composer {
  flex-shrink: 0;
}
.input-tip {
  margin: 6px 0 0;
  font-size: 12px;
  color: #94a3b8;
}
.user {
  color: #2563eb;
}
.assistant {
  color: #334155;
  white-space: pre-wrap;
}
.ask-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
.kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.kpi {
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: help;
}
.kpi span,
.kpi small {
  display: block;
  color: #94a3b8;
  font-size: 12px;
}
.kpi strong {
  display: block;
  margin: 4px 0 2px;
  font-size: 18px;
  color: #fff;
}
.preview {
  height: 380px;
  position: relative;
}
.chart-ops {
  display: flex;
  gap: 8px;
  margin: 12px 0 4px;
  flex-wrap: wrap;
}
.preview-wait {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #64748b;
  font-size: 13px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
  border-radius: 8px;
}
.preview-wait.overlay {
  position: absolute;
  inset: 0;
  background: rgba(248, 250, 252, 0.82);
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
.anomaly-list {
  margin: 6px 0 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.6;
}
</style>
