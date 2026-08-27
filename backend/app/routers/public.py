import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chart, Dashboard, Dataset
from app.services.data_service import chart_to_option, load_dataframe

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/dashboards/{token}")
def public_dashboard(token: str, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=404, detail="分享链接无效")
    item = db.query(Dashboard).filter(Dashboard.share_token == token).first()
    if not item:
        raise HTTPException(status_code=404, detail="分享链接无效")
    try:
        chart_ids = json.loads(item.chart_ids_json or "[]")
        layout = json.loads(item.layout_json or "[]")
        summary = json.loads(getattr(item, "summary_json", None) or "{}")
    except json.JSONDecodeError:
        chart_ids, layout, summary = [], [], {}
    if not isinstance(summary, dict):
        summary = {}
    charts = db.query(Chart).filter(Chart.id.in_(chart_ids or [0])).all()
    result = []
    for chart in charts:
        dataset = db.query(Dataset).filter(Dataset.id == chart.dataset_id).first()
        option = {}
        if dataset:
            try:
                option = chart_to_option(chart, load_dataframe(dataset))
            except Exception:
                option = {}
        result.append(
            {
                "id": chart.id,
                "title": chart.title,
                "insight": chart.insight,
                "x_field": chart.x_field,
                "option": option,
            }
        )
    return {
        "title": item.title,
        "description": item.description,
        "layout": layout,
        "kpis": summary.get("kpis") or [],
        "conclusion": summary.get("conclusion") or item.description,
        "charts": result,
    }
