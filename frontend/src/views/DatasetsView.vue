<template>
  <div class="page-header">
    <h2>数据集</h2>
    <div class="actions">
      <el-upload :show-file-list="false" accept=".csv,.xlsx,.xls" :http-request="onUpload" :disabled="uploading">
        <el-button type="primary" class="upload-btn" :loading="uploading">上传 CSV / Excel</el-button>
      </el-upload>
      <p class="format-hint">支持 .csv .xlsx .xls</p>
    </div>
  </div>
  <el-table :data="tableRows" v-loading="loading">
    <el-table-column prop="name" label="名称" min-width="120" />
    <el-table-column prop="filename" label="文件名" min-width="140" />
    <el-table-column prop="row_count" label="行数" width="90" />
    <el-table-column label="字段" min-width="220">
      <template #default="{ row }">
        <el-tooltip v-if="row.columns?.length" :content="row.columns.join('、')" placement="top" :show-after="200">
          <span class="fields-clip">{{ row.columns.join("、") }}</span>
        </el-tooltip>
        <span v-else class="muted">—</span>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="110">
      <template #default="{ row }">
        <el-tag v-if="row.parseOk" type="success" size="small">解析成功</el-tag>
        <el-tag v-else type="danger" size="small">解析失败</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="280">
      <template #default="{ row }">
        <template v-if="row.parseOk">
          <el-button link type="primary" @click="openPreview(row.id)">预览</el-button>
          <el-button link type="primary" @click="goAsk(row.id)">AI 问答</el-button>
          <el-button link type="primary" @click="goStudio(row.id)">做图</el-button>
          <el-button link class="btn-delete" @click="remove(row)">删除</el-button>
        </template>
        <el-button v-else link class="btn-delete" @click="dismissFail(row.filename)">移除</el-button>
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
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessageBox } from "element-plus";
import { datasetApi, type Dataset } from "../api";
import { toastError, toastSuccess, toastWarning } from "../utils/notify";

interface FailRow {
  id: number;
  name: string;
  filename: string;
  row_count: string;
  columns: string[];
  parseOk: false;
}

const datasets = ref<Dataset[]>([]);
const failed = ref<FailRow[]>([]);
const loading = ref(false);
const uploading = ref(false);
const previewVisible = ref(false);
const previewCols = ref<string[]>([]);
const previewRows = ref<Record<string, unknown>[]>([]);
const router = useRouter();

const tableRows = computed(() => [
  ...failed.value,
  ...datasets.value.map((item) => ({ ...item, parseOk: true as const })),
]);

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
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  if (!["csv", "xlsx", "xls"].includes(ext)) {
    toastError("仅支持 .csv .xlsx .xls 文件");
    return;
  }
  if (datasets.value.some((item) => item.filename === filename)) {
    await ElMessageBox.alert(`文件「${filename}」已上传过，请勿重复上传。`, "文件名重复", {
      type: "warning",
      confirmButtonText: "知道了",
    });
    return;
  }
  uploading.value = true;
  try {
    await datasetApi.upload(options.file, options.file.name.replace(/\.[^.]+$/, ""));
    toastSuccess("上传成功，解析完成");
    await load();
  } catch (error: any) {
    const detail = error.response?.data?.detail || "上传失败，文件无法解析";
    if (error.response?.status === 409) {
      await ElMessageBox.alert(detail, "文件名重复", { type: "warning", confirmButtonText: "知道了" });
      return;
    }
    failed.value.unshift({
      id: -Date.now(),
      name: filename.replace(/\.[^.]+$/, ""),
      filename,
      row_count: "—",
      columns: [],
      parseOk: false,
    });
    toastError(typeof detail === "string" ? detail : "解析出错，请检查文件是否损坏");
  } finally {
    uploading.value = false;
  }
}

function dismissFail(filename: string) {
  failed.value = failed.value.filter((item) => item.filename !== filename);
  toastWarning("已移除失败记录");
}

async function openPreview(id: number) {
  try {
    const { data } = await datasetApi.preview(id);
    previewCols.value = data.columns;
    previewRows.value = data.rows;
    previewVisible.value = true;
  } catch (error: any) {
    toastError(error.response?.data?.detail || "预览失败");
  }
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
    toastSuccess("已删除");
    await load();
  } catch (error: any) {
    toastError(error.response?.data?.detail || "删除失败");
  }
}

onMounted(load);
</script>

<style scoped>
.actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.upload-btn:hover {
  filter: brightness(1.06);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.28);
}
.format-hint {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}
.fields-clip {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
  cursor: default;
}
.muted {
  color: #94a3b8;
}
</style>
