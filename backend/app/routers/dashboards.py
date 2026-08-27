import json
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chart, Dashboard, Dataset, User
from app.schemas import DashboardCreate, DashboardGenerate, DashboardOut, DashboardUpdate
from app.security import get_current_user
from app.services.ai_service import local_chart_conclusion, recommend_with_features
from app.services.data_service import aggregate_series, load_dataframe

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])


def _parse_chart_ids(raw: str) -> list[int]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        return data.get("chart_ids") or []
    return data if isinstance(data, list) else []


def _parse_layout(item: Dashboard, chart_ids: list[int]) -> list[dict]:
    try:
        layout = json.loads(getattr(item, "layout_json", None) or "[]")
    except json.JSONDecodeError:
        layout = []
    if layout:
        return layout
    result = []
    for index, cid in enumerate(chart_ids):
        result.append({"i": str(cid), "x": (index % 2) * 6, "y": (index // 2) * 8, "w": 6, "h": 8, "chart_id": cid})
    return result


def _parse_summary(item: Dashboard) -> dict:
    try:
        data = json.loads(getattr(item, "summary_json", None) or "{}")
    except json.JSONDecodeError:
        data = {}
    return data if isinstance(data, dict) else {}


def _professional_layout(chart_ids: list[int]) -> list[dict]:
    if not chart_ids:
        return []
    layout = [{"i": str(chart_ids[0]), "x": 0, "y": 0, "w": 12, "h": 12, "chart_id": chart_ids[0]}]
    y = 12
    rest = chart_ids[1:]
    for index, cid in enumerate(rest):
        last_odd = index == len(rest) - 1 and len(rest) % 2 == 1
        width = 12 if last_odd else 6
        x = 0 if last_odd else (index % 2) * 6
        layout.append({"i": str(cid), "x": x, "y": y, "w": width, "h": 11, "chart_id": cid})
        if last_odd or index % 2 == 1:
            y += 11
    return layout


def _to_out(item: Dashboard) -> DashboardOut:
    chart_ids = _parse_chart_ids(item.chart_ids_json)
    summary = _parse_summary(item)
    return DashboardOut(
        id=item.id,
        title=item.title,
        description=item.description,
        chart_ids=chart_ids,
        layout=_parse_layout(item, chart_ids),
        share_token=getattr(item, "share_token", "") or "",
        kpis=summary.get("kpis") or [],
        conclusion=summary.get("conclusion") or "",
        created_at=item.created_at,
    )


def _owned_ids(db: Session, user_id: int, chart_ids: list[int]) -> list[int]:
    owned = {
        c.id
        for c in db.query(Chart).filter(Chart.owner_id == user_id, Chart.id.in_(chart_ids or [0])).all()
    }
    return [cid for cid in chart_ids if cid in owned]


@router.post("", response_model=DashboardOut)
def create_dashboard(payload: DashboardCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    chart_ids = _owned_ids(db, current.id, payload.chart_ids)
    layout = [item.model_dump() for item in payload.layout] if payload.layout else []
    item = Dashboard(
        title=payload.title,
        description=payload.description,
        chart_ids_json=json.dumps(chart_ids),
        layout_json=json.dumps(layout),
        summary_json="{}",
        owner_id=current.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.get("", response_model=list[DashboardOut])
def list_dashboards(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    items = db.query(Dashboard).filter(Dashboard.owner_id == current.id).order_by(Dashboard.id.desc()).all()
    return [_to_out(item) for item in items]


@router.post("/from-dataset", response_model=DashboardOut)
async def generate_dashboard(
    payload: DashboardGenerate, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id, Dataset.owner_id == current.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    df = load_dataframe(dataset)
    pack = await recommend_with_features(df)
    recs = pack.get("recommendations") or []
    if not recs:
        raise HTTPException(status_code=400, detail="当前数据无法生成图表，请检查字段")
    chart_ids: list[int] = []
    for rec in recs:
        chart = Chart(
            title=rec.get("title") or rec.get("reason") or "智能图表",
            chart_type=rec["chart_type"],
            x_field=rec["x_field"],
            y_field=rec.get("y_field") or "",
            aggregation=rec.get("aggregation") or "sum",
            dataset_id=dataset.id,
            owner_id=current.id,
        )
        try:
            grouped = aggregate_series(df, chart.x_field, chart.y_field, chart.aggregation)
        except ValueError:
            continue
        chart.insight = local_chart_conclusion(df, rec, grouped)
        db.add(chart)
        db.flush()
        chart_ids.append(chart.id)
    if not chart_ids:
        raise HTTPException(status_code=400, detail="无法根据推荐结果创建图表")
    summary = {"kpis": pack.get("kpis") or [], "conclusion": pack.get("conclusion") or "", "source": pack.get("source")}
    item = Dashboard(
        title=payload.title or f"{dataset.name} 经营看板",
        description=pack.get("conclusion") or f"基于「{dataset.name}」自动生成的分析看板",
        chart_ids_json=json.dumps(chart_ids),
        layout_json=json.dumps(_professional_layout(chart_ids)),
        summary_json=json.dumps(summary, ensure_ascii=False),
        owner_id=current.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.get("/{dashboard_id}", response_model=DashboardOut)
def get_dashboard(dashboard_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    item = db.query(Dashboard).filter(Dashboard.id == dashboard_id, Dashboard.owner_id == current.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="仪表盘不存在")
    return _to_out(item)


@router.put("/{dashboard_id}", response_model=DashboardOut)
def update_dashboard(
    dashboard_id: int,
    payload: DashboardUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    item = db.query(Dashboard).filter(Dashboard.id == dashboard_id, Dashboard.owner_id == current.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="仪表盘不存在")
    if payload.title is not None:
        item.title = payload.title
    if payload.description is not None:
        item.description = payload.description
    if payload.chart_ids is not None:
        item.chart_ids_json = json.dumps(_owned_ids(db, current.id, payload.chart_ids))
    if payload.layout is not None:
        item.layout_json = json.dumps([row.model_dump() for row in payload.layout])
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.post("/{dashboard_id}/share")
def share_dashboard(dashboard_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    item = db.query(Dashboard).filter(Dashboard.id == dashboard_id, Dashboard.owner_id == current.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="仪表盘不存在")
    item.share_token = secrets.token_urlsafe(16)
    db.commit()
    return {"share_token": item.share_token, "path": f"/share/{item.share_token}"}


@router.delete("/{dashboard_id}")
def delete_dashboard(dashboard_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    item = db.query(Dashboard).filter(Dashboard.id == dashboard_id, Dashboard.owner_id == current.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="仪表盘不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}
