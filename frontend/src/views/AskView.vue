<template>
  <div class="page-header">
    <h2>AI 自然语言问答</h2>
    <el-select v-model="datasetId" placeholder="选择数据集" style="width: 280px">
      <el-option v-for="item in datasets" :key="item.id" :label="item.name" :value="item.id" />
    </el-select>
  </div>
  <el-row :gutter="16">
    <el-col :span="9">
      <el-card class="ask-card">
        <p class="lead">用自然语言提问，系统会先识别数据特征，再出图并给出分析结论。</p>
        <div class="chips">
          <el-tag v-for="item in suggestions" :key="item" class="chip" @click="ask(item)">{{ item }}</el-tag>
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
          <div class="ask-actions">
            <el-checkbox v-model="saveChart">同时保存图表</el-checkbox>
            <el-button type="primary" :disabled="!datasetId" :loading="loading" @click="ask()">提问</el-button>
          </div>
        </div>
      </el-card>
    </el-col>
    <el-col :span="15">
      <el-card>
        <div class="kpis" v-if="kpis.length">
          <div v-for="item in kpis" :key="item.label" class="kpi">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <small>{{ item.hint }}</small>
          </div>
        </div>
        <div class="preview">
          <ChartPanel v-if="option && Object.keys(option).length" :option="option" />
          <el-empty v-else-if="!thinking" description="选择数据集并提问后，这里展示图表" />
          <div v-if="thinking" class="preview-wait" :class="{ overlay: !!(option && Object.keys(option).length) }">
            <ThinkingIndicator />
            <span>正在分析数据并生成图表</span>
          </div>
        </div>
        <ConclusionPanel :text="conclusion" :source="source" />
        <el-alert v-for="item in anomalies" :key="item.message" :title="item.message" type="warning" show-icon style="margin-top: 8px" />
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { aiApi, datasetApi, type Dataset } from "../api";
import ChartPanel from "../components/ChartPanel.vue";
import ConclusionPanel from "../components/ConclusionPanel.vue";
import ThinkingIndicator from "../components/ThinkingIndicator.vue";

const route = useRoute();
const datasets = ref<Dataset[]>([]);
const datasetId = ref<number>();
const EXAMPLE_QUESTION = "哪个地区销售额最高？近几个月趋势如何？";
const questionHint = `例如：${EXAMPLE_QUESTION}`;
const question = ref("");
const saveChart = ref(false);
const loading = ref(false);
const thinking = ref(false);
let askSeq = 0;
const option = ref<Record<string, unknown> | null>(null);
const conclusion = ref("");
const source = ref("");
const kpis = ref<{ label: string; value: string | number; hint?: string }[]>([]);
const anomalies = ref<any[]>([]);
const messages = ref<{ role: string; text: string }[]>([]);
const chatLogRef = ref<HTMLElement>();
const columns = computed(() => datasets.value.find((d) => d.id === datasetId.value)?.columns || []);
const suggestions = computed(() => {
  const cols = columns.value;
  if (!cols.length) return ["帮我概括这份数据的主要特征", "对比各分类指标高低", "看看时间趋势"];
  const metric = cols.find((col) => /销售|额|量|cost|sales|revenue|click/i.test(col)) || cols[cols.length - 1];
  const dim = cols.find((col) => /地区|区域|平台|产品|channel|region|platform/i.test(col)) || cols[0];
  return [`${dim} 的 ${metric} 谁最高？`, `${metric} 最近趋势怎么样？`, `${dim} 占比如何？`];
});

watch(datasetId, async (id) => {
  if (!id) return;
  const { data } = await aiApi.recommend(id);
  kpis.value = data.kpis || data.features?.kpis || [];
  conclusion.value = data.conclusion || "";
  source.value = data.source || "rules";
  option.value = null;
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

async function typeReply(full: string, seq: number) {
  messages.value.push({ role: "assistant", text: "" });
  const index = messages.value.length - 1;
  const step = Math.max(1, Math.ceil(full.length / 48));
  for (let i = 0; i < full.length; i += step) {
    if (seq !== askSeq) return;
    messages.value[index].text = full.slice(0, i + step);
    await scrollChatToBottom();
    await new Promise((resolve) => setTimeout(resolve, 22));
  }
  if (seq === askSeq) messages.value[index].text = full;
}

async function ask(preset?: string) {
  if (!datasetId.value || loading.value) return;
  const typed = question.value.trim();
  const text = (preset || typed || EXAMPLE_QUESTION).trim();
  if (preset) {
    question.value = preset;
  } else if (!typed || typed === EXAMPLE_QUESTION) {
    question.value = "";
  }
  const seq = ++askSeq;
  messages.value.push({ role: "user", text });
  thinking.value = true;
  loading.value = true;
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
    await typeReply(data.conclusion || data.insight || "已完成分析", seq);
    if (data.chart?.id) ElMessage.success("图表已保存，可加入仪表盘");
    await scrollChatToBottom();
  } catch (error: any) {
    if (seq === askSeq) ElMessage.error(error.response?.data?.detail || "提问失败");
  } finally {
    if (seq === askSeq) {
      thinking.value = false;
      loading.value = false;
    }
    await scrollChatToBottom();
  }
}

onMounted(load);
</script>

<style scoped>
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
  cursor: pointer;
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
</style>
