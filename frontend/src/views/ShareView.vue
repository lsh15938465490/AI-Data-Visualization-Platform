<template>
  <div class="share-page">
    <el-result v-if="loadError" icon="warning" title="分享链接无效或已失效" sub-title="无法打开该公开看板，请向创建者重新获取链接。">
      <template #extra>
        <el-button type="primary" @click="$router.push('/login')">返回登录</el-button>
      </template>
    </el-result>
    <template v-else>
      <div class="hero">
        <p class="kicker">公开分享看板</p>
        <h2>{{ title }}</h2>
        <p>{{ description }}</p>
      </div>
      <div class="kpis" v-if="kpis.length">
        <div v-for="item in kpis" :key="item.label" class="kpi">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.hint }}</small>
        </div>
      </div>
      <ConclusionPanel v-if="title" :text="conclusion" />
      <el-row :gutter="16">
        <el-col v-for="chart in charts" :key="chart.id" :span="12">
          <el-card class="tile" style="margin-bottom: 16px">
            <div class="tile-head">{{ chart.title }}</div>
            <ChartPanel :option="chart.option" lazy />
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { dashboardApi } from "../api";
import ChartPanel from "../components/ChartPanel.vue";
import ConclusionPanel from "../components/ConclusionPanel.vue";

const route = useRoute();
const title = ref("");
const description = ref("");
const conclusion = ref("");
const kpis = ref<{ label: string; value: string | number; hint?: string }[]>([]);
const charts = ref<any[]>([]);
const loadError = ref(false);

onMounted(async () => {
  try {
    const { data } = await dashboardApi.publicGet(String(route.params.token));
    title.value = data.title;
    description.value = data.description;
    conclusion.value = data.conclusion || data.description || "";
    kpis.value = data.kpis || [];
    charts.value = data.charts;
  } catch {
    loadError.value = true;
    title.value = "";
    description.value = "";
    conclusion.value = "";
    kpis.value = [];
    charts.value = [];
  }
});
</script>

<style scoped>
.share-page {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.hero {
  padding: 20px 24px;
  border-radius: 16px;
  background: linear-gradient(135deg, #0f172a, #1d4ed8);
  color: #fff;
  margin-bottom: 16px;
}
.kicker {
  margin: 0;
  color: #93c5fd;
  font-size: 12px;
}
.kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
.kpi {
  background: #fff;
  border-radius: 12px;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
}
.kpi span,
.kpi small {
  display: block;
  color: #64748b;
  font-size: 12px;
}
.kpi strong {
  display: block;
  margin: 4px 0;
  font-size: 20px;
}
.tile-head {
  font-weight: 600;
  margin-bottom: 8px;
}
</style>
