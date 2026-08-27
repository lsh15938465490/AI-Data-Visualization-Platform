# AI 数据可视化平台

基于自然语言与结构化数据的可视化分析系统。功能范围见 `需求文档/需求说明书.md`。

## 技术栈

- 前端：Vue 3 + Vite + TypeScript + Pinia + Vue Router + Element Plus + ECharts
- 后端：FastAPI + SQLAlchemy + SQLite + pandas
- 能力：CSV/Excel 上传、AI 问答与特征分析推荐、分析结论、拖拽仪表盘联动、分享、PDF/PNG 导出、异常 WebSocket 告警

## 启动

后端：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

前端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`，使用登录页展示的演示账号登录后，可上传测试数据集：

- CSV：`backend/sample_data/sales.csv`（区域产品销售，字段为英文（中文））
- Excel：`backend/sample_data/ad_campaign（广告投放）.xlsx`（广告投放效果，字段为英文（中文））

演示账号：`alice`　密码：`secret123`

可选环境变量（后端工作目录下的 `.env`）：

```
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

## 测试

```bash
cd backend
pytest -q
```
