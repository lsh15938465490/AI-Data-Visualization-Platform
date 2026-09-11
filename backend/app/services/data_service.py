from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import settings
from app.models import Chart, Dataset


def ensure_upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def detect_table_kind(data: bytes) -> str:
    if data.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = archive.namelist()
            if any(name.startswith("xl/") or name == "[Content_Types].xml" for name in names):
                return "xlsx"
        except zipfile.BadZipFile:
            pass
    if data.startswith(b"\xd0\xcf\x11\xe0"):
        return "xls"
    stripped = data.lstrip()
    if stripped.startswith((b"{", b"[")):
        try:
            json.loads(data.decode("utf-8-sig"))
            return "json"
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
    sample = data[:4096]
    if b"\x00" in sample:
        return ""
    control = sum(1 for byte in sample if byte < 9 or 13 < byte < 32)
    if sample and control / len(sample) > 0.1:
        return ""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = data.decode(encoding)
            first = next((line for line in text.splitlines() if line.strip()), "")
            if "," not in first and "\t" not in first:
                continue
            parsed = pd.read_csv(io.StringIO(text), nrows=5)
            if len(parsed.columns) >= 1:
                return "csv"
        except Exception:
            continue
    return ""


def dataframe_from_bytes(data: bytes) -> pd.DataFrame:
    kind = detect_table_kind(data)
    if kind == "xlsx":
        return pd.read_excel(io.BytesIO(data), engine="openpyxl")
    if kind == "xls":
        return pd.read_excel(io.BytesIO(data))
    if kind == "json":
        raw = json.loads(data.decode("utf-8-sig"))
        if isinstance(raw, dict):
            for key in ("data", "items", "records", "result"):
                if isinstance(raw.get(key), list):
                    raw = raw[key]
                    break
            else:
                raw = [raw]
        return pd.DataFrame(raw)
    if kind == "csv":
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return pd.read_csv(io.StringIO(data.decode(encoding)))
            except Exception:
                continue
        return pd.read_csv(io.BytesIO(data))
    raise ValueError("无法识别为 CSV / Excel / JSON 表格，请检查文件内容")


def load_dataframe(dataset: Dataset) -> pd.DataFrame:
    data = Path(dataset.filepath).read_bytes()
    return dataframe_from_bytes(data)


def infer_columns(df: pd.DataFrame) -> list[str]:
    return [str(col) for col in df.columns]


def to_preview(df: pd.DataFrame, limit: int = 50) -> dict[str, Any]:
    head = df.head(limit)
    preview = head.where(pd.notnull(head), None)
    return {
        "columns": infer_columns(df),
        "rows": preview.to_dict(orient="records"),
        "row_count": int(len(df)),
    }


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def categorical_columns(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]


def datetime_columns(df: pd.DataFrame) -> list[str]:
    result = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            result.append(str(col))
            continue
        if df[col].dtype == object:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() > 0.6:
                result.append(str(col))
    return result


def aggregate_series(df: pd.DataFrame, x_field: str, y_field: str, aggregation: str) -> pd.DataFrame:
    if x_field not in df.columns:
        raise ValueError(f"维度字段不存在: {x_field}")
    working = df.copy()
    if x_field in datetime_columns(df) and not pd.api.types.is_datetime64_any_dtype(working[x_field]):
        working[x_field] = pd.to_datetime(working[x_field], errors="coerce")

    if not y_field or y_field not in working.columns:
        grouped = working.groupby(x_field, dropna=False).size().reset_index(name="value")
        grouped[x_field] = grouped[x_field].astype(str)
        return grouped

    agg = aggregation.lower()
    if agg not in {"sum", "mean", "count", "max", "min"}:
        agg = "sum"

    if not pd.api.types.is_numeric_dtype(working[y_field]):
        converted = pd.to_numeric(working[y_field], errors="coerce")
        if agg != "count" and converted.notna().mean() < 0.5:
            raise ValueError(
                f"「{y_field}」是文本维度，不能做{agg}。请把指标 Y 改成数值列，例如 sales、impressions、clicks、cost、conversions、revenue。"
            )
        working[y_field] = converted

    if agg == "count":
        grouped = working.groupby(x_field, dropna=False)[y_field].count().reset_index(name="value")
    else:
        grouped = working.groupby(x_field, dropna=False)[y_field].agg(agg).reset_index(name="value")
    grouped[x_field] = grouped[x_field].astype(str)
    return grouped


def apply_filter(df: pd.DataFrame, field: str, value: str) -> pd.DataFrame:
    if not field or field not in df.columns or value == "":
        return df
    series = df[field].astype(str)
    return df[series == str(value)].copy()


CHART_PALETTE = [
    "#2563eb",
    "#0ea5e9",
    "#10b981",
    "#f59e0b",
    "#8b5cf6",
    "#f43f5e",
    "#14b8a6",
    "#eab308",
    "#6366f1",
    "#fb7185",
]


def apply_style(option: dict[str, Any], style: dict[str, Any] | None, title: str) -> dict[str, Any]:
    style = style or {}
    color = style.get("color") or "#3b82f6"
    legend = style.get("legend") or "bottom"
    display_title = style.get("title") or title
    option["title"] = {"text": display_title, "left": "left", "top": 8, "textStyle": {"fontSize": 14, "fontWeight": 600}}
    series_list = option.get("series") or []
    is_pie = any(item.get("type") == "pie" for item in series_list)
    option["color"] = CHART_PALETTE if is_pie else [color]
    if legend == "hidden":
        option["legend"] = {"show": False}
    elif legend == "top":
        option["legend"] = {"top": 28, "left": "center"}
    else:
        option["legend"] = {"bottom": 0}
    for series in series_list:
        series["progressive"] = 400
        series["progressiveThreshold"] = 200
        if series.get("type") == "pie":
            pie_names = []
            for index, row in enumerate(series.get("data") or []):
                if not isinstance(row, dict):
                    continue
                pie_names.append(str(row.get("name") or ""))
                row["itemStyle"] = {**(row.get("itemStyle") or {}), "color": CHART_PALETTE[index % len(CHART_PALETTE)]}
            if pie_names and legend != "hidden":
                option["legend"] = {**(option.get("legend") or {}), "data": pie_names}
            continue
        if series.get("type") in {"bar", "line"}:
            series["itemStyle"] = {"color": color}
            series["lineStyle"] = {"color": color}
        if series.get("type") == "line":
            series["areaStyle"] = {"opacity": 0.08}
    categories = (option.get("xAxis") or {}).get("data") or []
    if len(categories) > 12 and option.get("series") and option["series"][0].get("type") != "pie":
        slider_bottom = 6
        option["dataZoom"] = [
            {"type": "inside", "xAxisIndex": 0},
            {"type": "slider", "xAxisIndex": 0, "height": 18, "bottom": slider_bottom, "showDetail": False},
        ]
        if legend == "bottom":
            option["legend"] = {**(option.get("legend") or {}), "bottom": 32}
            option["grid"] = {**(option.get("grid") or {}), "bottom": 88}
        else:
            option["grid"] = {**(option.get("grid") or {}), "bottom": 48}
    return option


def chart_style(chart: Chart) -> dict[str, Any]:
    try:
        data = json.loads(chart.config_json or "{}")
    except json.JSONDecodeError:
        data = {}
    return data if isinstance(data, dict) else {}


def build_echarts_option(
    title: str,
    chart_type: str,
    grouped: pd.DataFrame,
    x_field: str,
    y_field: str = "",
) -> dict[str, Any]:
    categories = grouped[x_field].astype(str).tolist()
    values = [None if pd.isna(v) else round(float(v), 2) for v in grouped["value"].tolist()]
    chart_type = chart_type.lower()
    series_name = y_field or title
    option: dict[str, Any] = {
        "title": {"text": title, "left": "left", "top": 8, "textStyle": {"fontSize": 14, "fontWeight": 600, "color": "#0f172a"}},
        "tooltip": {
            "trigger": "axis" if chart_type != "pie" else "item",
            "axisPointer": {"type": "shadow" if chart_type == "bar" else "line"},
        },
        "grid": {"left": 24, "right": 24, "top": 52, "bottom": 56, "containLabel": True},
        "legend": {"bottom": 0, "data": [series_name]},
    }
    if chart_type == "pie":
        option["color"] = CHART_PALETTE
        option["legend"] = {"bottom": 0, "data": categories}
        option["series"] = [
            {
                "type": "pie",
                "name": series_name,
                "radius": ["35%", "65%"],
                "data": [
                    {
                        "name": name,
                        "value": value,
                        "itemStyle": {"color": CHART_PALETTE[index % len(CHART_PALETTE)]},
                    }
                    for index, (name, value) in enumerate(zip(categories, values))
                ],
                "progressive": 400,
            }
        ]
        return option
    if chart_type == "scatter":
        option["xAxis"] = _category_axis(x_field, categories)
        option["yAxis"] = {"type": "value", "name": series_name, "nameLocation": "middle", "nameGap": 48}
        option["series"] = [{"type": "scatter", "name": series_name, "symbolSize": 12, "data": values, "progressive": 400}]
        return option
    option["xAxis"] = _category_axis(x_field, categories)
    option["yAxis"] = {"type": "value", "name": series_name, "nameLocation": "middle", "nameGap": 48}
    option["series"] = [
        {
            "type": "line" if chart_type == "line" else "bar",
            "name": series_name,
            "data": values,
            "smooth": chart_type == "line",
            "barMaxWidth": 36,
            "itemStyle": {"borderRadius": [4, 4, 0, 0]} if chart_type != "line" else {},
            "progressive": 400,
            "progressiveThreshold": 200,
        }
    ]
    return option


def _category_axis(x_field: str, categories: list[str]) -> dict[str, Any]:
    return {
        "type": "category",
        "name": x_field,
        "nameLocation": "end",
        "nameGap": 12,
        "data": categories,
        "axisLabel": {
            "interval": 0,
            "hideOverlap": True,
            "width": 100,
            "overflow": "none",
        },
    }


def chart_to_option(
    chart: Chart,
    df: pd.DataFrame,
    filter_field: str = "",
    filter_value: str = "",
) -> dict[str, Any]:
    working = apply_filter(df, filter_field, filter_value)
    grouped = aggregate_series(working, chart.x_field, chart.y_field, chart.aggregation)
    option = build_echarts_option(chart.title, chart.chart_type, grouped, chart.x_field, chart.y_field)
    return apply_style(option, chart_style(chart), chart.title)


def dataset_to_out(dataset: Dataset) -> dict[str, Any]:
    try:
        columns = json.loads(dataset.columns_json or "[]")
    except json.JSONDecodeError:
        columns = []
    return {
        "id": dataset.id,
        "name": dataset.name,
        "filename": dataset.filename,
        "columns": columns,
        "row_count": dataset.row_count,
        "source_type": getattr(dataset, "source_type", None) or "file",
        "created_at": dataset.created_at,
    }
