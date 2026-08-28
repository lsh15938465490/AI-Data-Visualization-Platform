<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h2>登录</h2>
      <el-form @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">登录</el-button>
        <p class="credential-hint">登录账号：{{ demoUsername }}　密码：{{ demoPassword }}</p>
        <p class="demo-note">当前为演示账号，数据仅本地演示。</p>
      </el-form>
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
const username = ref(demoUsername);
const password = ref(demoPassword);
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
.credential-hint {
  margin: 16px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}
.demo-note {
  margin: 8px 0 0;
  color: #94a3b8;
  font-size: 12px;
}
</style>
