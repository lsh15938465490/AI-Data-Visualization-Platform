import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chart, Dataset, User
from app.schemas import ChartCreate, ChartOut, ChartStyle
from app.security import get_current_user
from app.services.data_service import chart_style, chart_to_option, load_dataframe

router = APIRouter(prefix="/api/charts", tags=["charts"])


def _to_out(chart: Chart, option: dict) -> ChartOut:
    return ChartOut(
        id=chart.id,
        title=chart.title,
        chart_type=chart.chart_type,
        x_field=chart.x_field,
        y_field=chart.y_field,
        aggregation=chart.aggregation,
        insight=chart.insight,
        dataset_id=chart.dataset_id,
        created_at=chart.created_at,
        option=option,
        style=chart_style(chart),
    )


def _option_for(chart: Chart, db: Session, filter_field: str = "", filter_value: str = "") -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == chart.dataset_id).first()
    if not dataset:
        return {}
    try:
        return chart_to_option(chart, load_dataframe(dataset), filter_field, filter_value)
    except Exception:
        return {}


@router.post("", response_model=ChartOut)
def create_chart(payload: ChartCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id, Dataset.owner_id == current.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    df = load_dataframe(dataset)
    chart = Chart(
        title=payload.title,
        chart_type=payload.chart_type,
        x_field=payload.x_field,
        y_field=payload.y_field,
        aggregation=payload.aggregation,
        dataset_id=dataset.id,
        owner_id=current.id,
    )
    try:
        option = chart_to_option(chart, df)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.add(chart)
    db.commit()
    db.refresh(chart)
    return _to_out(chart, option)


@router.get("", response_model=list[ChartOut])
def list_charts(
    filter_field: str = Query(""),
    filter_value: str = Query(""),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    charts = db.query(Chart).filter(Chart.owner_id == current.id).order_by(Chart.id.desc()).all()
    return [_to_out(chart, _option_for(chart, db, filter_field, filter_value)) for chart in charts]


@router.get("/{chart_id}", response_model=ChartOut)
def get_chart(
    chart_id: int,
    filter_field: str = Query(""),
    filter_value: str = Query(""),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    chart = db.query(Chart).filter(Chart.id == chart_id, Chart.owner_id == current.id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="图表不存在")
    return _to_out(chart, _option_for(chart, db, filter_field, filter_value))


@router.patch("/{chart_id}/style", response_model=ChartOut)
def update_style(
    chart_id: int,
    payload: ChartStyle,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    chart = db.query(Chart).filter(Chart.id == chart_id, Chart.owner_id == current.id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="图表不存在")
    style = {k: v for k, v in payload.model_dump().items() if v}
    if style.get("title"):
        chart.title = style["title"]
    chart.config_json = json.dumps(style, ensure_ascii=False)
    db.commit()
    db.refresh(chart)
    return _to_out(chart, _option_for(chart, db))


@router.delete("/{chart_id}")
def delete_chart(chart_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    chart = db.query(Chart).filter(Chart.id == chart_id, Chart.owner_id == current.id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="图表不存在")
    db.delete(chart)
    db.commit()
    return {"ok": True}
