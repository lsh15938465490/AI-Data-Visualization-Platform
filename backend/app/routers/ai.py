import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chart, Dataset, User
from app.schemas import AnalyzeRequest, AnalyzeResponse, ChartOut, ChatRequest, ChatResponse
from app.security import get_current_user
from app.services.ai_service import analyze_dataframe, chat_dataframe, recommend_with_features
from app.services.alerts import hub
from app.services.data_service import load_dataframe

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _chart_out(chart, option, style=None) -> ChartOut:
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
        style=style or {},
    )


async def _push_anomalies(user_id: int, anomalies: list[dict]) -> None:
    if not anomalies:
        return
    await hub.push(user_id, {"type": "anomaly", "items": anomalies})


@router.get("/recommend")
async def recommend(dataset_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == current.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return await recommend_with_features(load_dataframe(dataset))


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id, Dataset.owner_id == current.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    df = load_dataframe(dataset)
    result = await analyze_dataframe(df, payload.question)
    chart_out = None
    if payload.save:
        chart = Chart(
            title=result["title"],
            chart_type=result["chart_type"],
            x_field=result["x_field"],
            y_field=result["y_field"],
            aggregation=result["aggregation"],
            insight=result.get("conclusion") or result["insight"],
            config_json=json.dumps(result.get("style") or {}, ensure_ascii=False),
            dataset_id=dataset.id,
            owner_id=current.id,
        )
        db.add(chart)
        db.commit()
        db.refresh(chart)
        chart_out = _chart_out(chart, result["option"], result.get("style"))
    await _push_anomalies(current.id, result.get("anomalies") or [])
    return AnalyzeResponse(
        title=result["title"],
        chart_type=result["chart_type"],
        x_field=result["x_field"],
        y_field=result["y_field"],
        aggregation=result["aggregation"],
        insight=result["insight"],
        option=result["option"],
        conclusion=result.get("conclusion") or result["insight"],
        features=result.get("features") or {},
        recommendations=result.get("recommendations") or [],
        anomalies=result.get("anomalies") or [],
        chart=chart_out,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id, Dataset.owner_id == current.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    df = load_dataframe(dataset)
    spec = {
        "title": payload.title or payload.message[:40],
        "chart_type": payload.chart_type,
        "x_field": payload.x_field,
        "y_field": payload.y_field,
        "aggregation": payload.aggregation,
        "style": payload.style or {},
    }
    result = await chat_dataframe(df, payload.message, spec)
    chart_out = None
    if payload.save:
        chart = Chart(
            title=result["title"],
            chart_type=result["chart_type"],
            x_field=result["x_field"],
            y_field=result["y_field"],
            aggregation=result["aggregation"],
            insight=result.get("conclusion") or result.get("insight") or "",
            config_json=json.dumps(result.get("style") or {}, ensure_ascii=False),
            dataset_id=dataset.id,
            owner_id=current.id,
        )
        db.add(chart)
        db.commit()
        db.refresh(chart)
        chart_out = _chart_out(chart, result["option"], result.get("style"))
    await _push_anomalies(current.id, result.get("anomalies") or [])
    return ChatResponse(
        reply=result.get("reply") or result.get("insight") or "",
        title=result["title"],
        chart_type=result["chart_type"],
        x_field=result["x_field"],
        y_field=result["y_field"],
        aggregation=result["aggregation"],
        insight=result.get("insight") or "",
        option=result["option"],
        style=result.get("style") or {},
        conclusion=result.get("conclusion") or result.get("insight") or "",
        recommendations=result.get("recommendations") or [],
        anomalies=result.get("anomalies") or [],
        chart=chart_out,
    )
