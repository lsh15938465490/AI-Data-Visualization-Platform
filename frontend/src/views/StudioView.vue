<template>
  <div class="page-header">
    <h2>图表工作室</h2>
  </div>
  <el-row :gutter="16">
    <el-col :span="8">
      <el-card>
        <el-form label-position="top">
          <el-form-item label="数据集">
            <el-select v-model="datasetId" placeholder="选择数据集" style="width: 100%">
              <el-option v-for="item in datasets" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-form-item>
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
            <el-select v-model="yField" style="width: 100%" clearable>
              <el-option
                v-for="col in columns"
                :key="col"
                :label="numericColumns.includes(col) ? `${col}（数值）` : `${col}（文本）`"
                :value="col"
              />
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
          <el-button type="primary" :disabled="!datasetId" @click="createChart">生成并保存</el-button>
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
      <el-card>
        <div class="preview" ref="previewRef">
          <ChartPanel v-if="option && Object.keys(option).length" :option="option" />
          <el-empty v-else description="请选择数据集并生成图表" />
        </div>
        <ConclusionPanel :text="conclusion || insight" :source="recSource" />
        <el-alert v-for="item in anomalies" :key="item.message" :title="item.message" type="warning" show-icon style="margin-top: 8px" />
        <el-button style="margin-top: 12px" :disabled="!option" @click="exportPng">导出图片</el-button>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import html2canvas from "html2canvas";
import { aiApi, chartApi, datasetApi, type Dataset } from "../api";
import ChartPanel from "../components/ChartPanel.vue";
import ConclusionPanel from "../components/ConclusionPanel.vue";
import ThinkingIndicator from "../components/ThinkingIndicator.vue";

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
const recommendations = ref<any[]>([]);
const anomalies = ref<any[]>([]);
const messages = ref<{ role: string; text: string }[]>([]);
const previewRef = ref<HTMLElement>();
const chatLogRef = ref<HTMLElement>();
const numericColumns = ref<string[]>([]);
const columns = computed(() => datasets.value.find((d) => d.id === datasetId.value)?.columns || []);

watch(datasetId, async (id) => {
  if (!id) return;
  const [{ data: preview }, { data: rec }] = await Promise.all([
    datasetApi.preview(id),
    aiApi.recommend(id),
  ]);
  const cols = (preview.columns as string[]) || [];
  const numeric = cols.filter((col) =>
    (preview.rows as Record<string, unknown>[]).some((row) => typeof row[col] === "number")
  );
  numericColumns.value = numeric;
  xField.value = cols.find((col) => !numeric.includes(col)) || cols[0] || "";
  yField.value = numeric[0] || "";
  recommendations.value = rec.recommendations || [];
  conclusion.value = rec.conclusion || "";
  recSource.value = rec.source || "";
});

async function load() {
  const { data } = await datasetApi.list();
  datasets.value = data;
  const qid = Number(route.query.datasetId);
  if (qid) datasetId.value = qid;
  else if (data[0]) datasetId.value = data[0].id;
}

function applyRec(item: any) {
  chartType.value = item.chart_type;
  xField.value = item.x_field;
  yField.value = item.y_field;
  aggregation.value = item.aggregation;
  ElMessage.success("已应用推荐配置");
}

async function createChart() {
  if (!datasetId.value) return;
  try {
    const { data } = await chartApi.create({
      title: title.value,
      dataset_id: datasetId.value,
      chart_type: chartType.value,
      x_field: xField.value,
      y_field: yField.value,
      aggregation: aggregation.value,
    });
    option.value = data.option;
    insight.value = data.insight;
    conclusion.value = data.conclusion || data.insight;
    ElMessage.success("图表已保存");
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "生成失败");
  }
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
    messages.value.push({ role: "assistant", text: data.reply });
    await scrollChatToBottom();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "分析失败");
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
.preview {
  height: 420px;
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
