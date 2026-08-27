<template>
  <div class="page-header">
    <h2>AI 自然语言问答</h2>
    <el-select v-model="datasetId" placeholder="选择数据集" style="width: 280px">
      <el-option v-for="item in datasets" :key="item.id" :label="item.name" :value="item.id" />
    </el-select>
  </div>
  <el-row :gutter="16">
    <el-col :span="9">
      <el-card>
        <p class="lead">用自然语言提问，系统会先识别数据特征，再出图并给出分析结论。</p>
        <div class="chips">
          <el-tag v-for="item in suggestions" :key="item" class="chip" @click="ask(item)">{{ item }}</el-tag>
        </div>
        <div class="chat-log">
          <p v-for="(msg, index) in messages" :key="index" :class="msg.role">{{ msg.text }}</p>
        </div>
        <el-input v-model="question" type="textarea" :rows="4" placeholder="例如：哪个地区销售额最高？近几个月趋势如何？" />
        <div class="ask-actions">
          <el-checkbox v-model="saveChart">同时保存图表</el-checkbox>
          <el-button type="primary" :disabled="!datasetId" :loading="loading" @click="ask()">提问</el-button>
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
          <el-empty v-else description="选择数据集并提问后，这里展示图表" />
        </div>
        <ConclusionPanel :text="conclusion" :source="source" />
        <el-alert v-for="item in anomalies" :key="item.message" :title="item.message" type="warning" show-icon style="margin-top: 8px" />
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { aiApi, datasetApi, type Dataset } from "../api";
import ChartPanel from "../components/ChartPanel.vue";
import ConclusionPanel from "../components/ConclusionPanel.vue";

const route = useRoute();
const datasets = ref<Dataset[]>([]);
const datasetId = ref<number>();
const question = ref("");
const saveChart = ref(false);
const loading = ref(false);
const option = ref<Record<string, unknown> | null>(null);
const conclusion = ref("");
const source = ref("");
const kpis = ref<{ label: string; value: string | number; hint?: string }[]>([]);
const anomalies = ref<any[]>([]);
const messages = ref<{ role: string; text: string }[]>([]);
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

async function ask(preset?: string) {
  if (!datasetId.value) return;
  const text = (preset || question.value).trim();
  if (!text) return;
  question.value = text;
  messages.value.push({ role: "user", text });
  loading.value = true;
  try {
    const { data } = await aiApi.analyze({
      dataset_id: datasetId.value,
      question: text,
      save: saveChart.value,
    });
    option.value = data.option;
    conclusion.value = data.conclusion || data.insight || "";
    kpis.value = data.features?.kpis || kpis.value;
    anomalies.value = data.anomalies || [];
    messages.value.push({ role: "assistant", text: data.conclusion || data.insight || "已完成分析" });
    if (data.chart?.id) ElMessage.success("图表已保存，可加入仪表盘");
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "提问失败");
  } finally {
    loading.value = false;
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
.chat-log {
  max-height: 220px;
  overflow: auto;
  margin-bottom: 8px;
  font-size: 13px;
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
}
</style>
