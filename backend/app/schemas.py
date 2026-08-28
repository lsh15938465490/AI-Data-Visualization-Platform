from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DatasetOut(BaseModel):
    id: int
    name: str
    filename: str
    columns: list[str]
    row_count: int
    source_type: str = "file"
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetPreview(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int


class ChartCreate(BaseModel):
    title: str
    dataset_id: int
    chart_type: str = "bar"
    x_field: str = ""
    y_field: str = ""
    aggregation: str = "sum"
    save: bool = True


class ChartStyle(BaseModel):
    color: str = ""
    legend: str = "bottom"
    title: str = ""


class ChartUpdate(BaseModel):
    title: Optional[str] = None
    chart_type: Optional[str] = None
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    aggregation: Optional[str] = None


class ChartOut(BaseModel):
    id: int
    title: str
    chart_type: str
    x_field: str
    y_field: str
    aggregation: str
    insight: str
    dataset_id: int
    created_at: datetime
    option: dict[str, Any] = {}
    style: dict[str, Any] = {}

    model_config = {"from_attributes": True}


class AnalyzeRequest(BaseModel):
    dataset_id: int
    question: str
    save: bool = False


class AnalyzeResponse(BaseModel):
    title: str
    chart_type: str
    x_field: str
    y_field: str
    aggregation: str
    insight: str
    option: dict[str, Any]
    conclusion: str = ""
    features: dict[str, Any] = {}
    recommendations: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    chart: Optional[ChartOut] = None


class ChatRequest(BaseModel):
    dataset_id: int
    message: str
    title: str = ""
    chart_type: str = "bar"
    x_field: str = ""
    y_field: str = ""
    aggregation: str = "sum"
    style: dict[str, Any] = {}
    save: bool = False


class ChatResponse(BaseModel):
    reply: str
    title: str
    chart_type: str
    x_field: str
    y_field: str
    aggregation: str
    insight: str
    option: dict[str, Any]
    style: dict[str, Any] = {}
    conclusion: str = ""
    recommendations: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    chart: Optional[ChartOut] = None


class LayoutItem(BaseModel):
    i: str
    x: int
    y: int
    w: int
    h: int
    chart_id: int


class DashboardCreate(BaseModel):
    title: str
    description: str = ""
    chart_ids: list[int] = []
    layout: list[LayoutItem] = []


class DashboardGenerate(BaseModel):
    dataset_id: int
    title: str = ""


class DashboardOut(BaseModel):
    id: int
    title: str
    description: str
    chart_ids: list[int]
    layout: list[dict[str, Any]] = []
    share_token: str = ""
    kpis: list[dict[str, Any]] = []
    conclusion: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    chart_ids: Optional[list[int]] = None
    layout: Optional[list[LayoutItem]] = None
