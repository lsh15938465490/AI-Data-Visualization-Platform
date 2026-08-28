<template>
  <div class="charts-page" v-loading="loading" element-loading-text="正在加载已保存图表…">
    <div class="page-header">
      <h2>我的图表</h2>
      <el-button type="primary" @click="$router.push('/studio')">去图表工作室</el-button>
    </div>
    <el-empty v-if="!loading && !charts.length" description="暂无已保存图表。请在图表工作室点击「生成并保存」，或在 AI 问答勾选同时保存。" />
    <el-row v-else :gutter="20" class="chart-grid">
      <el-col v-for="item in charts" :key="item.id" :span="8" class="chart-col">
        <el-card shadow="never" class="chart-card">
          <div class="card-head">
            <h3>{{ item.title || "未命名图表" }}</h3>
            <el-tag size="small" type="info" effect="plain">{{ typeLabel(item.chart_type) }}</el-tag>
          </div>
          <p class="source">来自数据集：{{ datasetName(item.dataset_id) }}</p>
          <p class="meta">{{ item.x_field }} / {{ item.y_field || "—" }}</p>
          <div class="thumb">
            <ChartPanel v-if="item.option && Object.keys(item.option).length" :option="item.option" lazy />
            <el-empty v-else description="无法预览" />
          </div>
          <div class="card-actions">
            <el-button type="primary" link @click="openEdit(item)">编辑</el-button>
            <el-button link class="btn-delete" @click="remove(item)">删除</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="editVisible" title="编辑图表" width="520px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="图表类型">
          <el-select v-model="editForm.chart_type" style="width: 100%">
            <el-option label="柱状图" value="bar" />
            <el-option label="折线图" value="line" />
            <el-option label="饼图" value="pie" />
            <el-option label="散点图" value="scatter" />
          </el-select>
        </el-form-item>
        <el-form-item label="维度 X">
          <el-select v-model="editForm.x_field" style="width: 100%">
            <el-option v-for="col in editColumns" :key="col" :label="col" :value="col" />
          </el-select>
        </el-form-item>
        <el-form-item label="指标 Y">
          <el-select v-model="editForm.y_field" style="width: 100%">
            <el-option v-for="col in editYColumns" :key="col" :label="col" :value="col" />
          </el-select>
        </el-form-item>
        <el-form-item label="聚合">
          <el-select v-model="editForm.aggregation" style="width: 100%">
            <el-option label="求和" value="sum" />
            <el-option label="平均" value="mean" />
            <el-option label="计数" value="count" />
            <el-option label="最大" value="max" />
            <el-option label="最小" value="min" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessageBox } from "element-plus";
import { chartApi, datasetApi, type ChartItem, type Dataset } from "../api";
import ChartPanel from "../components/ChartPanel.vue";
import { toastError, toastSuccess } from "../utils/notify";

const charts = ref<ChartItem[]>([]);
const datasets = ref<Dataset[]>([]);
const loading = ref(false);
const saving = ref(false);
const editVisible = ref(false);
const editId = ref(0);
const editColumns = ref<string[]>([]);
const editNumeric = ref<string[]>([]);
const editForm = reactive({
  title: "",
  chart_type: "bar",
  x_field: "",
  y_field: "",
  aggregation: "sum",
});
const editYColumns = computed(() => (editForm.aggregation === "count" ? editColumns.value : editNumeric.value));

function typeLabel(type?: string) {
  return ({ bar: "柱状对比", line: "趋势", pie: "结构占比", scatter: "相关分析" } as Record<string, string>)[type || ""] || "图表";
}

function datasetName(id: number) {
  return datasets.value.find((item) => item.id === id)?.name || "未知数据集";
}

function isNumericValue(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return true;
  if (typeof value === "string" && value.trim() && /^-?\d+(\.\d+)?$/.test(value.trim())) return true;
  return false;
}

async function load() {
  loading.value = true;
  try {
    const [c, s] = await Promise.all([chartApi.list(), datasetApi.list()]);
    charts.value = (c.data || []).filter((item) => item.id > 0);
    datasets.value = s.data || [];
  } catch (error: any) {
    toastError(error.response?.data?.detail || "加载图表失败");
  } finally {
    loading.value = false;
  }
}

async function openEdit(item: ChartItem) {
  editId.value = item.id;
  editForm.title = item.title;
  editForm.chart_type = item.chart_type;
  editForm.x_field = item.x_field;
  editForm.y_field = item.y_field;
  editForm.aggregation = item.aggregation || "sum";
  try {
    const { data } = await datasetApi.preview(item.dataset_id);
    const cols = (data.columns as string[]) || [];
    const rows = (data.rows as Record<string, unknown>[]) || [];
    editColumns.value = cols;
    editNumeric.value = cols.filter((col) => rows.some((row) => isNumericValue(row[col])));
  } catch {
    editColumns.value = [item.x_field, item.y_field].filter(Boolean);
    editNumeric.value = item.y_field ? [item.y_field] : [];
  }
  editVisible.value = true;
}

async function saveEdit() {
  if (!editForm.x_field || !editForm.y_field) {
    toastError("请选择 X 维度和 Y 指标");
    return;
  }
  saving.value = true;
  try {
    await chartApi.update(editId.value, { ...editForm });
    toastSuccess("图表已更新");
    editVisible.value = false;
    await load();
  } catch (error: any) {
    toastError(error.response?.data?.detail || "保存失败，请检查字段是否匹配");
  } finally {
    saving.value = false;
  }
}

async function remove(item: ChartItem) {
  try {
    await ElMessageBox.confirm(`确定删除「${item.title || "未命名图表"}」吗？删除后不可恢复。`, "删除确认", {
      type: "warning",
      confirmButtonText: "确定删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await chartApi.remove(item.id);
    toastSuccess("图表已删除");
    await load();
  } catch (error: any) {
    toastError(error.response?.data?.detail || "删除失败");
  }
}

onMounted(load);
</script>

<style scoped>
.charts-page {
  min-height: calc(100vh - 88px);
}
.chart-col {
  margin-bottom: 24px;
}
.chart-card {
  height: 100%;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.chart-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--card-shadow-hover) !important;
}
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.card-head h3 {
  margin: 0;
  flex: 1;
  min-width: 0;
  font-size: 15px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meta {
  margin: 0 0 8px;
  color: #94a3b8;
  font-size: 12px;
}
.source {
  margin: 0 0 2px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
}
.thumb {
  height: 220px;
  border-radius: 8px;
  overflow: hidden;
  background: #f8fafc;
}
.thumb :deep(.chart-wrap),
.thumb :deep(.chart-box) {
  min-height: 220px;
  height: 220px;
}
.card-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}
</style>
