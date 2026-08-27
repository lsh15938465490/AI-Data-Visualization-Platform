<template>
  <div class="page-header">
    <h2>仪表盘</h2>
    <div>
      <el-button @click="genVisible = true">从数据集一键生成</el-button>
      <el-button type="primary" @click="dialogVisible = true">新建仪表盘</el-button>
    </div>
  </div>
  <el-row :gutter="16">
    <el-col v-for="item in dashboards" :key="item.id" :span="8">
      <el-card shadow="hover" class="board-card">
        <div class="card-kicker">{{ item.chart_ids.length }} 张图表</div>
        <h3>{{ item.title }}</h3>
        <p class="desc">{{ item.conclusion || item.description || "暂无分析结论" }}</p>
        <div class="card-actions">
          <el-button type="primary" link @click="$router.push(`/dashboards/${item.id}`)">打开看板</el-button>
          <el-button type="danger" link @click="remove(item.id)">删除</el-button>
        </div>
      </el-card>
    </el-col>
  </el-row>

  <el-dialog v-model="dialogVisible" title="新建仪表盘">
    <el-form label-position="top">
      <el-form-item label="标题">
        <el-input v-model="form.title" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" />
      </el-form-item>
      <el-form-item label="选择图表">
        <el-select v-model="form.chart_ids" multiple style="width: 100%">
          <el-option v-for="chart in charts" :key="chart.id" :label="chart.title" :value="chart.id" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="create">创建</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="genVisible" title="从数据集生成专业看板">
    <el-form label-position="top">
      <el-form-item label="数据集">
        <el-select v-model="genForm.dataset_id" style="width: 100%">
          <el-option v-for="item in datasets" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="看板标题">
        <el-input v-model="genForm.title" placeholder="可留空，将使用数据集名称" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="genVisible = false">取消</el-button>
      <el-button type="primary" :loading="genLoading" @click="generate">生成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { chartApi, dashboardApi, datasetApi, type ChartItem, type DashboardItem, type Dataset } from "../api";

const router = useRouter();
const dashboards = ref<DashboardItem[]>([]);
const charts = ref<ChartItem[]>([]);
const datasets = ref<Dataset[]>([]);
const dialogVisible = ref(false);
const genVisible = ref(false);
const genLoading = ref(false);
const form = reactive({ title: "销售看板", description: "", chart_ids: [] as number[] });
const genForm = reactive({ dataset_id: undefined as number | undefined, title: "" });

async function load() {
  const [d, c, s] = await Promise.all([dashboardApi.list(), chartApi.list(), datasetApi.list()]);
  dashboards.value = d.data;
  charts.value = c.data;
  datasets.value = s.data;
  if (!genForm.dataset_id && s.data[0]) genForm.dataset_id = s.data[0].id;
}

async function create() {
  const { data } = await dashboardApi.create({ ...form });
  dialogVisible.value = false;
  ElMessage.success("仪表盘已创建");
  await load();
  router.push(`/dashboards/${data.id}`);
}

async function generate() {
  if (!genForm.dataset_id) return;
  genLoading.value = true;
  try {
    const { data } = await dashboardApi.fromDataset({
      dataset_id: genForm.dataset_id,
      title: genForm.title,
    });
    genVisible.value = false;
    ElMessage.success("看板已生成");
    await load();
    router.push(`/dashboards/${data.id}`);
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "生成失败");
  } finally {
    genLoading.value = false;
  }
}

async function remove(id: number) {
  try {
    await ElMessageBox.confirm("确定删除该仪表盘吗？", "删除确认", {
      type: "warning",
      confirmButtonText: "确定删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  await dashboardApi.remove(id);
  ElMessage.success("仪表盘已删除");
  await load();
}

onMounted(load);
</script>

<style scoped>
.board-card h3 {
  margin: 4px 0 8px;
}
.card-kicker {
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
}
.desc {
  min-height: 48px;
  color: #64748b;
  font-size: 13px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: pre-wrap;
}
.card-actions {
  display: flex;
  justify-content: space-between;
}
</style>
