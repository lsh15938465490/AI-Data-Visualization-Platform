import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: () => import("../views/LoginView.vue") },
    { path: "/register", redirect: "/login" },
    { path: "/share/:token", component: () => import("../views/ShareView.vue") },
    {
      path: "/",
      component: () => import("../layouts/MainLayout.vue"),
      children: [
        { path: "", redirect: "/datasets" },
        { path: "datasets", component: () => import("../views/DatasetsView.vue") },
        { path: "ask", component: () => import("../views/AskView.vue") },
        { path: "studio", component: () => import("../views/StudioView.vue") },
        { path: "dashboards", component: () => import("../views/DashboardsView.vue") },
        { path: "dashboards/:id", component: () => import("../views/DashboardDetailView.vue") },
      ],
    },
  ],
});

router.beforeEach(async (to) => {
  const publicPages = ["/login"];
  const auth = useAuthStore();
  if (to.path.startsWith("/share")) return true;
  if (!publicPages.includes(to.path) && !auth.token) {
    return "/login";
  }
  if (auth.token && !auth.user) {
    try {
      await auth.fetchMe();
    } catch {
      auth.logout();
      return "/login";
    }
  }
  return true;
});

export default router;
