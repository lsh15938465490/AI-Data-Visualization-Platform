import http from "./http";

export interface User {
  id: number;
  username: string;
}

export interface Dataset {
  id: number;
  name: string;
  filename: string;
  columns: string[];
  row_count: number;
  source_type?: string;
  created_at: string;
}

export interface ChartItem {
  id: number;
  title: string;
  chart_type: string;
  x_field: string;
  y_field: string;
  aggregation: string;
  insight: string;
  dataset_id: number;
  created_at: string;
  option: Record<string, unknown>;
  style?: Record<string, unknown>;
}

export interface LayoutItem {
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
  chart_id: number;
}

export interface DashboardItem {
  id: number;
  title: string;
  description: string;
  chart_ids: number[];
  layout: LayoutItem[];
  share_token: string;
  kpis?: { label: string; value: string | number; hint?: string }[];
  conclusion?: string;
  created_at: string;
}

export const authApi = {
  login: (username: string, password: string) => {
    const form = new URLSearchParams();
    form.set("username", username);
    form.set("password", password);
    return http.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
  me: () => http.get<User>("/auth/me"),
};

export const datasetApi = {
  list: () => http.get<Dataset[]>("/datasets"),
  upload: (file: File, name: string) => {
    const data = new FormData();
    data.append("file", file);
    data.append("name", name);
    return http.post<Dataset>("/datasets/upload", data);
  },
  preview: (id: number) => http.get(`/datasets/${id}/preview`),
  remove: (id: number) => http.delete(`/datasets/${id}`),
};

export const chartApi = {
  list: (filter?: { field?: string; value?: string }) =>
    http.get<ChartItem[]>("/charts", {
      params: { filter_field: filter?.field || "", filter_value: filter?.value || "" },
    }),
  create: (payload: Record<string, unknown>) => http.post<ChartItem>("/charts", payload),
  get: (id: number, filter?: { field?: string; value?: string }) =>
    http.get<ChartItem>(`/charts/${id}`, {
      params: { filter_field: filter?.field || "", filter_value: filter?.value || "" },
    }),
  update: (id: number, payload: Record<string, unknown>) => http.patch<ChartItem>(`/charts/${id}`, payload),
  remove: (id: number) => http.delete(`/charts/${id}`),
};

export const aiApi = {
  analyze: (payload: { dataset_id: number; question: string; save?: boolean }) =>
    http.post("/ai/analyze", payload),
  chat: (payload: Record<string, unknown>) => http.post("/ai/chat", payload),
  recommend: (datasetId: number) => http.get("/ai/recommend", { params: { dataset_id: datasetId } }),
};

export const dashboardApi = {
  list: () => http.get<DashboardItem[]>("/dashboards"),
  create: (payload: { title: string; description: string; chart_ids: number[] }) =>
    http.post<DashboardItem>("/dashboards", payload),
  fromDataset: (payload: { dataset_id: number; title?: string }) =>
    http.post<DashboardItem>("/dashboards/from-dataset", payload),
  get: (id: number) => http.get<DashboardItem>(`/dashboards/${id}`),
  update: (id: number, payload: Record<string, unknown>) => http.put<DashboardItem>(`/dashboards/${id}`, payload),
  share: (id: number) => http.post<{ share_token: string; path: string }>(`/dashboards/${id}/share`),
  remove: (id: number) => http.delete(`/dashboards/${id}`),
  publicGet: (token: string) => http.get(`/public/dashboards/${token}`),
};
