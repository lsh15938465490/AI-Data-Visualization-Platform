<template>
  <section class="conclusion">
    <div class="conclusion-head">
      <span>分析结论</span>
      <el-tag v-if="source" size="small" type="info">{{ source === "llm" ? "大模型" : "特征规则" }}</el-tag>
    </div>
    <p v-if="!text" class="placeholder">提问或生成图表后，这里会输出结构化结论。</p>
    <ul v-else>
      <li v-for="(line, index) in lines" :key="index">{{ line }}</li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ text?: string; source?: string }>();

const lines = computed(() =>
  (props.text || "")
    .split(/\n+/)
    .map((item) => item.replace(/^[\s\-\d\.、]+/, "").trim())
    .filter(Boolean)
);
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
.placeholder {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}
ul {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  font-size: 13px;
  line-height: 1.7;
}
</style>
