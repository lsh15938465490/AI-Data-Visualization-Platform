<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h2>登录</h2>
      <el-form label-width="72px" autocomplete="off" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="username" placeholder="请输入用户名" name="login-username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="password"
            type="password"
            show-password
            placeholder="请输入密码"
            name="login-password"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">登录</el-button>
        </el-form-item>
      </el-form>
      <p class="credential-hint">演示账号：{{ demoUsername }} / {{ demoPassword }}</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { authApi } from "../api";
import { useAuthStore } from "../stores/auth";

const demoUsername = "alice";
const demoPassword = "secret123";
const username = ref("");
const password = ref("");
const loading = ref(false);
const router = useRouter();
const auth = useAuthStore();

async function onSubmit() {
  loading.value = true;
  try {
    const { data } = await authApi.login(username.value, password.value);
    auth.setSession(data.access_token, data.user);
    router.push("/datasets");
  } catch (error: any) {
    ElMessage({ message: error.response?.data?.detail || "登录失败", type: "error", duration: 4000, showClose: true });
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-card {
  width: 440px;
}
.auth-card h2 {
  margin: 0 0 20px;
  line-height: 1.2;
}
.auth-card :deep(.el-form-item__label) {
  justify-content: flex-end;
  text-align: right;
}
.auth-card :deep(.el-form-item) {
  margin-bottom: 18px;
}
.auth-card :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}
.auth-card :deep(.el-input__wrapper) {
  width: 100%;
}
.credential-hint {
  margin: 12px 0 0 72px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
  text-align: center;
}
</style>
