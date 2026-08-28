<template>
  <section class="conclusion">
    <div class="conclusion-head">
      <span>分析结论</span>
      <div class="actions">
        <el-tag v-if="source" size="small" type="info">{{ source === "llm" ? "大模型" : "特征规则" }}</el-tag>
        <slot name="actions" />
        <el-button v-if="copyable && text" link type="primary" @click="copy">复制</el-button>
        <el-button v-if="collapsible && text" link type="primary" @click="expanded = !expanded">
          {{ expanded ? "收起" : "展开" }}
        </el-button>
      </div>
    </div>
    <p v-if="!text" class="placeholder">{{ emptyText }}</p>
    <div v-else class="body" :class="{ collapsed: collapsible && !expanded }">
      <ul>
        <li v-for="(line, index) in lines" :key="index" :class="{ alert: isAlert(line) }">{{ line }}</li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { toastSuccess, toastError } from "../utils/notify";

const props = withDefaults(
  defineProps<{
    text?: string;
    source?: string;
    copyable?: boolean;
    collapsible?: boolean;
    emptyText?: string;
  }>(),
  {
    copyable: false,
    collapsible: false,
    emptyText: "提问或生成图表后，这里会输出结构化结论。",
  },
);

const expanded = ref(false);

const lines = computed(() =>
  (props.text || "")
    .split(/\n+|(?=\d+[\.、]\s)/)
    .map((item) => item.replace(/^[\s\-\d\.、]+/, "").trim())
    .filter(Boolean),
);

function isAlert(line: string) {
  return /异常|偏离|极端|波动极大|标准差|异常值/.test(line);
}

async function copy() {
  try {
    await navigator.clipboard.writeText(props.text || "");
    toastSuccess("分析报告已复制");
  } catch {
    toastError("复制失败，请手动选择文本");
  }
}
</script>

<style scoped>
.conclusion {
  margin-top: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
  border: 1px solid #dbe7ff;
}
.conclusion-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 700;
  color: #1e3a8a;
  margin-bottom: 8px;
}
.actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
.placeholder {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}
.body {
  max-height: 280px;
  overflow: auto;
}
.body.collapsed {
  max-height: 96px;
}
ul {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  font-size: 13px;
  line-height: 1.7;
}
.alert {
  color: #dc2626;
  font-weight: 600;
}
</style>
