from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.security import create_access_token, hash_password
from app.models import User


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr("app.config.settings.upload_dir", str(tmp_path))
    monkeypatch.setattr("app.services.data_service.settings.upload_dir", str(tmp_path))

    with TestClient(app) as test_client:
        db = TestingSession()
        user = User(username="alice", hashed_password=hash_password("secret123"))
        db.add(user)
        db.commit()
        db.close()
        yield test_client
    app.dependency_overrides.clear()


def auth_header():
    return {"Authorization": f"Bearer {create_access_token('alice')}"}


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["llm"] in {"none", "deepseek", "openai"}


def test_deepseek_key_alias(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_KEY_API", "sk-test-deepseek")
    from app.config import Settings

    conf = Settings(_env_file=None)
    assert conf.llm_provider == "deepseek"
    assert conf.llm_model == "deepseek-chat"
    assert "deepseek.com" in conf.llm_base_url
    assert conf.llm_api_key == "sk-test-deepseek"


def test_login_and_me(client):
    resp = client.post("/api/auth/login", data={"username": "alice", "password": "secret123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


def test_register_removed(client):
    resp = client.post("/api/auth/register", json={"username": "bob", "password": "secret123"})
    assert resp.status_code == 404


def test_dataset_chart_ai_flow(client, tmp_path):
    csv_path = tmp_path / "sales.csv"
    pd.DataFrame(
        {
            "region": ["华东", "华东", "华北", "华北"],
            "sales": [100, 120, 80, 90],
            "month": ["2024-01", "2024-02", "2024-01", "2024-02"],
        }
    ).to_csv(csv_path, index=False)

    with csv_path.open("rb") as fh:
        upload = client.post(
            "/api/datasets/upload",
            headers=auth_header(),
            files={"file": ("sales.csv", fh, "text/csv")},
            data={"name": "销售数据"},
        )
    assert upload.status_code == 200, upload.text
    dataset_id = upload.json()["id"]
    assert upload.json()["row_count"] == 4

    preview = client.get(f"/api/datasets/{dataset_id}/preview", headers=auth_header())
    assert preview.status_code == 200
    assert "region" in preview.json()["columns"]

    chart = client.post(
        "/api/charts",
        headers=auth_header(),
        json={
            "title": "区域销售额",
            "dataset_id": dataset_id,
            "chart_type": "bar",
            "x_field": "region",
            "y_field": "sales",
            "aggregation": "sum",
        },
    )
    assert chart.status_code == 200, chart.text
    assert chart.json()["option"]["series"]

    analyze = client.post(
        "/api/ai/analyze",
        headers=auth_header(),
        json={"dataset_id": dataset_id, "question": "各地区销售额占比", "save": True},
    )
    assert analyze.status_code == 200, analyze.text
    assert analyze.json()["chart_type"] in {"bar", "line", "pie", "scatter"}
    assert analyze.json()["chart"]["id"]

    board = client.post(
        "/api/dashboards",
        headers=auth_header(),
        json={"title": "销售看板", "description": "demo", "chart_ids": [analyze.json()["chart"]["id"]]},
    )
    assert board.status_code == 200
    assert board.json()["chart_ids"]


def test_upload_sample_csv_and_excel(client):
    sample_dir = Path(__file__).resolve().parents[1] / "sample_data"
    csv_file = sample_dir / "sales.csv"
    xlsx_file = sample_dir / "ad_campaign（广告投放）.xlsx"
    if not xlsx_file.exists():
        xlsx_file = sample_dir / "ad_campaign.xlsx"

    with csv_file.open("rb") as fh:
        csv_resp = client.post(
            "/api/datasets/upload",
            headers=auth_header(),
            files={"file": ("sales.csv", fh, "text/csv")},
            data={"name": "区域销售明细"},
        )
    assert csv_resp.status_code == 200, csv_resp.text
    csv_body = csv_resp.json()
    assert csv_body["row_count"] == 24
    cols = csv_body["columns"]
    assert any(name in cols for name in ("渠道", "channel"))
    assert any(name in cols for name in ("产品", "product"))

    with xlsx_file.open("rb") as fh:
        xlsx_resp = client.post(
            "/api/datasets/upload",
            headers=auth_header(),
            files={
                "file": (
                    "ad_campaign.xlsx",
                    fh,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={"name": "广告投放效果"},
        )
    assert xlsx_resp.status_code == 200, xlsx_resp.text
    xlsx_body = xlsx_resp.json()
    assert xlsx_body["row_count"] == 15
    xcols = xlsx_body["columns"]
    assert any(name in xcols for name in ("平台", "platform"))
    assert any(name in xcols for name in ("曝光量", "impressions"))
    assert csv_body["columns"] != xlsx_body["columns"]


def test_chart_rejects_text_metric(client, tmp_path):
    csv_path = tmp_path / "ads.csv"
    pd.DataFrame(
        {
            "date": ["2024-03-01", "2024-03-02"],
            "platform": ["抖音", "百度"],
            "impressions": [1000, 20],
        }
    ).to_csv(csv_path, index=False)
    with csv_path.open("rb") as fh:
        upload = client.post(
            "/api/datasets/upload",
            headers=auth_header(),
            files={"file": ("ads.csv", fh, "text/csv")},
            data={"name": "广告"},
        )
    chart = client.post(
        "/api/charts",
        headers=auth_header(),
        json={
            "title": "错误指标",
            "dataset_id": upload.json()["id"],
            "chart_type": "line",
            "x_field": "date",
            "y_field": "platform",
            "aggregation": "sum",
        },
    )
    assert chart.status_code == 400
    assert "文本维度" in chart.json()["detail"]


def test_dataset_chat_share(client, tmp_path):
    dataset_id = _upload_sales(client, tmp_path)
    rec = client.get("/api/ai/recommend", headers=auth_header(), params={"dataset_id": dataset_id})
    assert rec.status_code == 200
    assert rec.json()["recommendations"]

    chat = client.post(
        "/api/ai/chat",
        headers=auth_header(),
        json={
            "dataset_id": dataset_id,
            "message": "把颜色改成橙色",
            "title": "区域销售",
            "chart_type": "bar",
            "x_field": "region",
            "y_field": "sales",
            "aggregation": "sum",
            "save": True,
        },
    )
    assert chat.status_code == 200, chat.text
    assert chat.json()["style"]["color"] == "#f97316"
    assert chat.json()["chart"]["id"]

    board = client.post(
        "/api/dashboards",
        headers=auth_header(),
        json={"title": "分享看板", "chart_ids": [chat.json()["chart"]["id"]]},
    )
    shared = client.post(f"/api/dashboards/{board.json()['id']}/share", headers=auth_header())
    assert shared.status_code == 200
    token = shared.json()["share_token"]
    public = client.get(f"/api/public/dashboards/{token}")
    assert public.status_code == 200
    assert public.json()["title"] == "分享看板"


def test_upload_duplicate_name_and_content_sniff(client, tmp_path):
    csv_path = tmp_path / "plain.txt"
    csv_path.write_text("region,sales\n华东,100\n华南,200\n", encoding="utf-8")
    with csv_path.open("rb") as fh:
        first = client.post(
            "/api/datasets/upload",
            headers=auth_header(),
            files={"file": ("sales.txt", fh, "text/plain")},
            data={"name": "无后缀销售"},
        )
    assert first.status_code == 200, first.text
    assert first.json()["row_count"] == 2

    with csv_path.open("rb") as fh:
        dup = client.post(
            "/api/datasets/upload",
            headers=auth_header(),
            files={"file": ("sales.txt", fh, "text/plain")},
            data={"name": "重复"},
        )
    assert dup.status_code == 409
    assert "已上传过" in dup.json()["detail"]

    bad = client.post(
        "/api/datasets/upload",
        headers=auth_header(),
        files={"file": ("notes.csv", b"\x00\x01\x02not-a-table", "application/octet-stream")},
        data={"name": "假csv"},
    )
    assert bad.status_code == 400


def _upload_sales(client, tmp_path):
    csv_path = tmp_path / "board.csv"
    pd.DataFrame(
        {
            "region": ["华东", "华东", "华北", "华北"],
            "sales": [100, 120, 80, 90],
            "month": ["2024-01", "2024-02", "2024-01", "2024-02"],
        }
    ).to_csv(csv_path, index=False)
    with csv_path.open("rb") as fh:
        upload = client.post(
            "/api/datasets/upload",
            headers=auth_header(),
            files={"file": ("board.csv", fh, "text/csv")},
            data={"name": "看板销售"},
        )
    assert upload.status_code == 200, upload.text
    return upload.json()["id"]


def test_recommend_features_and_conclusion(client, tmp_path):
    dataset_id = _upload_sales(client, tmp_path)
    rec = client.get("/api/ai/recommend", headers=auth_header(), params={"dataset_id": dataset_id})
    assert rec.status_code == 200, rec.text
    body = rec.json()
    assert body["features"]["row_count"] == 4
    assert body["kpis"]
    assert body["conclusion"]
    assert body["recommendations"]
    analyze = client.post(
        "/api/ai/analyze",
        headers=auth_header(),
        json={"dataset_id": dataset_id, "question": "各地区销售额谁最高"},
    )
    assert analyze.status_code == 200
    assert analyze.json()["conclusion"]


def test_llm_recommend_then_dashboard(client, tmp_path, monkeypatch):
    async def fake_llm(prompt: str, temperature: float = 0.2):
        return (
            '{"conclusion":"模型已分析特征：华东销售额更高。","recommendations":['
            '{"title":"区域对比","chart_type":"bar","x_field":"region","y_field":"sales",'
            '"aggregation":"sum","reason":"llm特征推荐"}]}'
        )

    monkeypatch.setattr("app.services.ai_service.llm_complete", fake_llm)
    dataset_id = _upload_sales(client, tmp_path)
    rec = client.get("/api/ai/recommend", headers=auth_header(), params={"dataset_id": dataset_id})
    assert rec.status_code == 200
    assert rec.json()["source"] == "llm"
    assert rec.json()["recommendations"][0]["reason"] == "llm特征推荐"

    board = client.post(
        "/api/dashboards/from-dataset",
        headers=auth_header(),
        json={"dataset_id": dataset_id, "title": "专业看板"},
    )
    assert board.status_code == 200, board.text
    assert board.json()["title"] == "专业看板"
    assert board.json()["kpis"]
    assert board.json()["conclusion"]
    assert len(board.json()["chart_ids"]) >= 1
    assert board.json()["layout"][0]["w"] == 12


def test_recommend_rules_without_llm(client, tmp_path, monkeypatch):
    async def no_llm(prompt: str, temperature: float = 0.2):
        return None

    monkeypatch.setattr("app.services.ai_service.llm_complete", no_llm)
    dataset_id = _upload_sales(client, tmp_path)
    rec = client.get("/api/ai/recommend", headers=auth_header(), params={"dataset_id": dataset_id})
    assert rec.status_code == 200
    body = rec.json()
    assert body["source"] == "rules"
    assert body["recommendations"]
    assert body["conclusion"]


def test_public_dashboard_invalid_token(client):
    resp = client.get("/api/public/dashboards/not-a-token")
    assert resp.status_code == 404
    assert "title" not in (resp.json() if isinstance(resp.json(), dict) else {})


