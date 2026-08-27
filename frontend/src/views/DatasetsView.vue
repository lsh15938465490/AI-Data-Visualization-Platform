<template>
  <div class="page-header">
    <h2>数据集</h2>
    <div class="actions">
      <el-upload :show-file-list="false" :http-request="onUpload">
        <el-button type="primary">上传 CSV / Excel</el-button>
      </el-upload>
    </div>
  </div>
  <el-table :data="datasets" v-loading="loading">
    <el-table-column prop="name" label="名称" />
    <el-table-column prop="filename" label="文件名" />
    <el-table-column prop="row_count" label="行数" width="90" />
    <el-table-column label="字段">
      <template #default="{ row }">{{ row.columns.join(", ") }}</template>
    </el-table-column>
    <el-table-column label="操作" width="280">
      <template #default="{ row }">
        <el-button link type="primary" @click="openPreview(row.id)">预览</el-button>
        <el-button link type="primary" @click="goAsk(row.id)">AI 问答</el-button>
        <el-button link type="primary" @click="goStudio(row.id)">做图</el-button>
        <el-button link type="danger" @click="remove(row)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>

  <el-dialog v-model="previewVisible" title="数据预览" width="80%">
    <el-table :data="previewRows" max-height="420">
      <el-table-column v-for="col in previewCols" :key="col" :prop="col" :label="col" />
    </el-table>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { datasetApi, type Dataset } from "../api";

const datasets = ref<Dataset[]>([]);
const loading = ref(false);
const previewVisible = ref(false);
const previewCols = ref<string[]>([]);
const previewRows = ref<Record<string, unknown>[]>([]);
const router = useRouter();

async function load() {
  loading.value = true;
  try {
    const { data } = await datasetApi.list();
    datasets.value = data;
  } finally {
    loading.value = false;
  }
}

async function onUpload(options: { file: File }) {
  const filename = options.file.name;
  if (datasets.value.some((item) => item.filename === filename)) {
    await ElMessageBox.alert(`文件「${filename}」已上传过，请勿重复上传。`, "文件名重复", {
      type: "warning",
      confirmButtonText: "知道了",
    });
    return;
  }
  try {
    await datasetApi.upload(options.file, options.file.name.replace(/\.[^.]+$/, ""));
    ElMessage.success("上传成功");
    await load();
  } catch (error: any) {
    const detail = error.response?.data?.detail || "上传失败";
    if (error.response?.status === 409) {
      await ElMessageBox.alert(detail, "文件名重复", { type: "warning", confirmButtonText: "知道了" });
      return;
    }
    ElMessage.error(detail);
  }
}

async function openPreview(id: number) {
  const { data } = await datasetApi.preview(id);
  previewCols.value = data.columns;
  previewRows.value = data.rows;
  previewVisible.value = true;
}

function goAsk(id: number) {
  router.push({ path: "/ask", query: { datasetId: String(id) } });
}

function goStudio(id: number) {
  router.push({ path: "/studio", query: { datasetId: String(id) } });
}

async function remove(row: Dataset) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${row.filename || row.name}」吗？删除后不可恢复。`,
      "删除确认",
      {
        type: "warning",
        confirmButtonText: "确定删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }
  try {
    await datasetApi.remove(row.id);
    ElMessage.success("已删除");
    await load();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || "删除失败");
  }
}

onMounted(load);
</script>

<style scoped>
.actions {
  display: flex;
  gap: 8px;
}
</style>
