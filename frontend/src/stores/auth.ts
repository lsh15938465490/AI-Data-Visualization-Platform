import { defineStore } from "pinia";
import { authApi, type User } from "../api";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("token") || "",
    user: null as User | null,
  }),
  actions: {
    setSession(token: string, user: User) {
      this.token = token;
      this.user = user;
      localStorage.setItem("token", token);
    },
    logout() {
      this.token = "";
      this.user = null;
      localStorage.removeItem("token");
    },
    async fetchMe() {
      if (!this.token) return;
      const { data } = await authApi.me();
      this.user = data;
    },
  },
});
