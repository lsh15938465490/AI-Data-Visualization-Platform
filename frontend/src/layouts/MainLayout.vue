<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="brand">AI 可视化平台</div>
      <el-menu :router="true" :default-active="route.path" background-color="#0f172a" text-color="#cbd5e1" active-text-color="#60a5fa">
        <el-menu-item index="/datasets">数据集</el-menu-item>
        <el-menu-item index="/ask">AI 问答</el-menu-item>
        <el-menu-item index="/studio">图表工作室</el-menu-item>
        <el-menu-item index="/dashboards">仪表盘</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container class="body">
      <el-header class="header">
        <span>{{ auth.user?.username }}</span>
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
.main {
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}
</style>
