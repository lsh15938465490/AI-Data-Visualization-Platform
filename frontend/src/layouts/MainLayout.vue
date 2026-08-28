<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="brand">AI 可视化平台</div>
      <el-menu
        :router="true"
        :default-active="route.path.startsWith('/dashboards') ? '/dashboards' : route.path"
        background-color="#0f172a"
        text-color="#cbd5e1"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/datasets">
          <el-icon><FolderOpened /></el-icon>
          <span>数据集</span>
        </el-menu-item>
        <el-menu-item index="/ask">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 问答</span>
        </el-menu-item>
        <el-menu-item index="/studio">
          <el-icon><DataAnalysis /></el-icon>
          <span>图表工作室</span>
        </el-menu-item>
        <el-menu-item index="/charts">
          <el-icon><PieChart /></el-icon>
          <span>我的图表</span>
        </el-menu-item>
        <el-menu-item index="/dashboards">
          <el-icon><Monitor /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container class="body">
      <el-header class="header">
        <div class="user-block">
          <span class="user-name">演示账号</span>
          <span class="demo-hint">当前为演示账号，数据仅本地演示</span>
        </div>
        <el-button link type="primary" @click="logout">退出</el-button>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";
import { ElNotification } from "element-plus";
import { ChatDotRound, DataAnalysis, FolderOpened, Monitor, PieChart } from "@element-plus/icons-vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
let socket: WebSocket | null = null;

function logout() {
  auth.logout();
  socket?.close();
  router.push("/login");
}

onMounted(() => {
  if (!auth.token) return;
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocol}://${location.host}/api/ws/alerts?token=${auth.token}`);
  socket.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "anomaly") {
      for (const item of payload.items || []) {
        ElNotification({ title: "指标异常告警", message: item.message, type: "warning" });
      }
    }
  };
});

onBeforeUnmount(() => socket?.close());
</script>

<style scoped>
.layout {
  height: 100%;
  overflow: hidden;
}
.aside {
  height: 100%;
  overflow: hidden;
  background: #0f172a;
  color: #fff;
}
.brand {
  padding: 20px 16px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.aside :deep(.el-menu-item) {
  margin: 4px 10px;
  border-radius: 8px;
  height: 44px;
}
.aside :deep(.el-menu-item.is-active) {
  background: #2563eb !important;
  color: #fff !important;
  font-weight: 600;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.35);
}
.body {
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}
.header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}
.user-block {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.3;
}
.user-name {
  font-weight: 600;
  color: #0f172a;
}
.demo-hint {
  font-size: 12px;
  color: #64748b;
}
.main {
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}
</style>
