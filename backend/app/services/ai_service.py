from __future__ import annotations

import json
from typing import Any

import httpx
import pandas as pd

from app.config import settings
from app.services.data_service import (
    aggregate_series,
    apply_style,
    build_echarts_option,
    categorical_columns,
    datetime_columns,
    numeric_columns,
)


def infer_spec(df: pd.DataFrame, question: str) -> dict[str, Any]:
    cats = categorical_columns(df)
    nums = numeric_columns(df)
    times = datetime_columns(df)
    q = question.lower()

    chart_type = "bar"
    if any(k in q for k in ("趋势", "变化", "折线", "时间", "月份", "trend", "line")):
        chart_type = "line"
    elif any(k in q for k in ("占比", "比例", "饼", "pie")):
        chart_type = "pie"
    elif any(k in q for k in ("散点", "相关", "scatter")):
        chart_type = "scatter"

    x_field = times[0] if times and chart_type == "line" else (cats[0] if cats else df.columns[0])
    y_field = nums[0] if nums else ""

    for col in list(df.columns):
        if str(col) in question:
            if str(col) in nums:
                y_field = str(col)
            else:
                x_field = str(col)

    aggregation = "sum"
    if any(k in q for k in ("平均", "均值", "mean")):
        aggregation = "mean"
    elif any(k in q for k in ("数量", "次数", "count")):
        aggregation = "count"

    title = question.strip()[:40] or "智能图表"
    return {
        "title": title,
        "chart_type": chart_type,
        "x_field": str(x_field),
        "y_field": str(y_field),
        "aggregation": aggregation,
    }


def local_insight(df: pd.DataFrame, spec: dict[str, Any], grouped: pd.DataFrame) -> str:
    conclusion = local_chart_conclusion(df, spec, grouped)
    return conclusion.split("\n")[0].strip()


def local_chart_conclusion(df: pd.DataFrame, spec: dict[str, Any], grouped: pd.DataFrame) -> str:
    x_field = spec["x_field"]
    y_field = spec.get("y_field") or "记录数"
    if grouped.empty:
        return "当前条件下没有可汇总的数据，请检查筛选条件或字段选择。"
    ranked = grouped.sort_values("value", ascending=False)
    top = ranked.iloc[0]
    low = ranked.iloc[-1]
    total = float(grouped["value"].sum())
    mean = float(grouped["value"].mean())
    lines = [
        f"按「{x_field}」对「{y_field}」做 {spec.get('aggregation') or 'sum'} 汇总，得到 {len(grouped)} 个分组，合计 {round(total, 2)}，均值 {round(mean, 2)}。",
        f"最高贡献来自 {top[x_field]}（{round(float(top['value']), 2)}），最低为 {low[x_field]}（{round(float(low['value']), 2)}）。",
    ]
    if len(grouped) >= 2 and mean:
        share = float(top["value"]) / total * 100 if total else 0
        lines.append(f"头部项约占合计的 {share:.1f}%，可用于判断集中度。")
        last = grouped.iloc[-1]["value"]
        prev = grouped.iloc[-2]["value"]
        if prev:
            ratio = (float(last) - float(prev)) / abs(float(prev)) * 100
            lines.append(f"末段相对前一段变化 {ratio:+.1f}%，建议结合业务周期解读。")
    missing = int(df[x_field].isna().sum()) if x_field in df.columns else 0
    if missing:
        lines.append(f"维度「{x_field}」存在 {missing} 条空值，可能影响分组完整性。")
    return "\n".join(lines)


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    cats = categorical_columns(df)
    nums = numeric_columns(df)
    times = datetime_columns(df)
    columns = []
    for col in df.columns:
        series = df[col]
        numeric = pd.api.types.is_numeric_dtype(series)
        info: dict[str, Any] = {
            "name": str(col),
            "dtype": str(series.dtype),
            "missing_rate": round(float(series.isna().mean()), 4),
            "unique_count": int(series.nunique(dropna=True)),
            "kind": "numeric" if numeric else ("datetime" if str(col) in times else "categorical"),
        }
        if numeric:
            values = pd.to_numeric(series, errors="coerce")
            info.update(
                {
                    "min": None if values.dropna().empty else round(float(values.min()), 4),
                    "max": None if values.dropna().empty else round(float(values.max()), 4),
                    "mean": None if values.dropna().empty else round(float(values.mean()), 4),
                    "sum": None if values.dropna().empty else round(float(values.sum()), 4),
                }
            )
        else:
            top = series.dropna().astype(str).value_counts().head(3)
            info["top_values"] = [{"value": idx, "count": int(val)} for idx, val in top.items()]
        columns.append(info)
    kpis: list[dict[str, Any]] = [{"label": "数据行数", "value": int(len(df)), "hint": f"{len(df.columns)} 个字段"}]
    if nums:
        first = nums[0]
        values = pd.to_numeric(df[first], errors="coerce")
        kpis.append({"label": f"{first} 合计", "value": round(float(values.sum()), 2), "hint": "全表求和"})
        kpis.append({"label": f"{first} 均值", "value": round(float(values.mean()), 2), "hint": "全表平均"})
    if cats:
        col = cats[0]
        top = df[col].dropna().astype(str).value_counts()
        if not top.empty:
            kpis.append({"label": f"{col} 主导项", "value": str(top.index[0]), "hint": f"出现 {int(top.iloc[0])} 次"})
    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": [str(c) for c in df.columns],
        "numeric_fields": nums,
        "categorical_fields": cats,
        "datetime_fields": times,
        "field_profiles": columns[:16],
        "kpis": kpis[:4],
    }


def local_dataset_conclusion(features: dict[str, Any]) -> str:
    nums = features.get("numeric_fields") or []
    cats = features.get("categorical_fields") or []
    times = features.get("datetime_fields") or []
    lines = [
        f"数据集共 {features.get('row_count', 0)} 行、{features.get('column_count', 0)} 列。"
        f"数值字段 {len(nums)} 个，类别字段 {len(cats)} 个，时间字段 {len(times)} 个。"
    ]
    if times and nums:
        lines.append(f"检测到时间列「{times[0]}」与指标「{nums[0]}」，适合先看趋势再拆维度。")
    elif cats and nums:
        lines.append(f"建议以「{cats[0]}」对比「{nums[0]}」，并用占比图观察结构。")
    elif nums:
        lines.append("以数值分布和相关关系为主，可补充散点或区间统计。")
    else:
        lines.append("数值指标较少，当前更适合做分类计数与结构分析。")
    profiles = features.get("field_profiles") or []
    sparse = [item["name"] for item in profiles if item.get("missing_rate", 0) >= 0.1]
    if sparse:
        lines.append("空值偏高的字段：" + "、".join(sparse[:4]) + "，解读时需谨慎。")
    return "\n".join(lines)


def recommend_charts(df: pd.DataFrame) -> list[dict[str, Any]]:
    cats = categorical_columns(df)
    nums = numeric_columns(df)
    times = datetime_columns(df)
    recs: list[dict[str, Any]] = []
    if times and nums:
        recs.append(
            {
                "chart_type": "line",
                "title": f"{nums[0]}趋势",
                "x_field": times[0],
                "y_field": nums[0],
                "aggregation": "sum",
                "reason": "检测到时间序列，推荐折线图观察趋势",
            }
        )
    if cats and nums:
        recs.append(
            {
                "chart_type": "bar",
                "title": f"{cats[0]}对比",
                "x_field": cats[0],
                "y_field": nums[0],
                "aggregation": "sum",
                "reason": "维度 + 指标，推荐柱状图对比高低",
            }
        )
        recs.append(
            {
                "chart_type": "pie",
                "title": f"{cats[0]}占比",
                "x_field": cats[0],
                "y_field": nums[0],
                "aggregation": "sum",
                "reason": "适合查看各分类占比",
            }
        )
    if len(nums) >= 2:
        recs.append(
            {
                "chart_type": "scatter",
                "title": f"{nums[0]}与{nums[1]}",
                "x_field": nums[0],
                "y_field": nums[1],
                "aggregation": "sum",
                "reason": "两个数值字段，推荐散点观察相关",
            }
        )
    return recs[:4]


def _parse_llm_json(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = cleaned.find(start_char)
        end = cleaned.rfind(end_char)
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def sanitize_recommendations(df: pd.DataFrame, items: list[Any]) -> list[dict[str, Any]]:
    columns = {str(col) for col in df.columns}
    valid_types = {"bar", "line", "pie", "scatter"}
    valid_agg = {"sum", "mean", "count", "max", "min"}
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        chart_type = str(item.get("chart_type") or "").lower()
        x_field = str(item.get("x_field") or "")
        y_field = str(item.get("y_field") or "")
        aggregation = str(item.get("aggregation") or "sum").lower()
        if chart_type not in valid_types or x_field not in columns:
            continue
        if y_field and y_field not in columns:
            continue
        if aggregation not in valid_agg:
            aggregation = "sum"
        result.append(
            {
                "chart_type": chart_type,
                "title": str(item.get("title") or "")[:40] or f"{x_field}分析",
                "x_field": x_field,
                "y_field": y_field,
                "aggregation": aggregation,
                "reason": str(item.get("reason") or "基于数据特征推荐"),
            }
        )
    return result[:4]


async def llm_complete(prompt: str, temperature: float = 0.2) -> str | None:
    if not settings.llm_api_key:
        return None
    url = settings.llm_base_url + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    payload = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


async def recommend_with_features(df: pd.DataFrame) -> dict[str, Any]:
    features = profile_dataframe(df)
    fallback = recommend_charts(df)
    conclusion = local_dataset_conclusion(features)
    source = "rules"
    prompt = (
        "你是数据分析师。先根据数据特征判断字段角色（时间/维度/指标），再推荐 3 到 4 个图表。"
        "必须只返回 JSON 对象，格式："
        '{"conclusion":"中文分析结论，分条，不超过220字","recommendations":['
        '{"title":"标题","chart_type":"line|bar|pie|scatter","x_field":"必须是已有字段",'
        '"y_field":"必须是已有字段","aggregation":"sum|mean|count","reason":"一句话理由"}]}'
        f"\n数据特征: {json.dumps(features, ensure_ascii=False, default=str)}"
    )
    text = await llm_complete(prompt)
    parsed = _parse_llm_json(text) if text else None
    recs = fallback
    if isinstance(parsed, dict):
        llm_recs = sanitize_recommendations(df, parsed.get("recommendations") or [])
        if llm_recs:
            recs = llm_recs
            source = "llm"
        if parsed.get("conclusion"):
            conclusion = str(parsed["conclusion"]).strip()
            source = "llm" if source == "llm" or parsed.get("conclusion") else source
    elif isinstance(parsed, list):
        llm_recs = sanitize_recommendations(df, parsed)
        if llm_recs:
            recs = llm_recs
            source = "llm"
    return {
        "features": features,
        "kpis": features.get("kpis") or [],
        "conclusion": conclusion,
        "recommendations": recs,
        "source": source,
    }


def detect_anomalies(df: pd.DataFrame, spec: dict[str, Any]) -> list[dict[str, Any]]:
    y_field = spec.get("y_field") or ""
    x_field = spec.get("x_field") or ""
    if not y_field or y_field not in df.columns:
        return []
    grouped = aggregate_series(df, x_field or df.columns[0], y_field, spec.get("aggregation") or "sum")
    if len(grouped) < 3:
        return []
    values = pd.to_numeric(grouped["value"], errors="coerce")
    mean = values.mean()
    std = values.std(ddof=0)
    if not std:
        return []
    alerts = []
    for _, row in grouped.iterrows():
        z = (float(row["value"]) - float(mean)) / float(std)
        if abs(z) >= 1.5:
            alerts.append(
                {
                    "dimension": str(row[x_field or grouped.columns[0]]),
                    "metric": y_field,
                    "value": round(float(row["value"]), 2),
                    "zscore": round(z, 2),
                    "message": f"{row[x_field or grouped.columns[0]]} 的 {y_field}={round(float(row['value']), 2)}，偏离均值 {z:.1f} 个标准差",
                }
            )
    return alerts


COLOR_WORDS = {
    "蓝": "#3b82f6",
    "红": "#ef4444",
    "绿": "#22c55e",
    "橙": "#f97316",
    "紫": "#a855f7",
    "青": "#06b6d4",
}


def apply_chat_tweak(message: str, spec: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    text = message.strip()
    style = dict(spec.get("style") or {})
    if "标题" in text:
        for sep in ("改成", "改为", "为", "：", ":"):
            if sep in text:
                title = text.split(sep, 1)[-1].strip(" \"'")
                if title:
                    spec["title"] = title
                    style["title"] = title
                    spec["style"] = style
                    return spec, f"已将标题更新为「{title}」。"
    if "图例" in text:
        if any(k in text for k in ("隐藏", "不要", "关闭")):
            style["legend"] = "hidden"
            spec["style"] = style
            return spec, "已隐藏图例。"
        if "顶" in text:
            style["legend"] = "top"
            spec["style"] = style
            return spec, "图例已移到顶部。"
        style["legend"] = "bottom"
        spec["style"] = style
        return spec, "图例已移到底部。"
    for word, color in COLOR_WORDS.items():
        if word in text or color in text:
            style["color"] = color
            spec["style"] = style
            return spec, f"已将主色调整为{word}色，图表已即时更新。"
    return spec, None


async def analyze_dataframe(df: pd.DataFrame, question: str, style: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = infer_spec(df, question)
    grouped = aggregate_series(df, spec["x_field"], spec["y_field"], spec["aggregation"])
    option = apply_style(
        build_echarts_option(spec["title"], spec["chart_type"], grouped, spec["x_field"], spec.get("y_field") or ""),
        style,
        spec["title"],
    )
    insight = local_insight(df, spec, grouped)
    conclusion = local_chart_conclusion(df, spec, grouped)
    sample = grouped.head(20).to_dict(orient="records")
    llm_text = await llm_complete(
        "你是数据分析助手。根据用户问题和汇总数据，用中文给出分析结论，分 3 条以内，不超过 220 字，"
        "要包含最高贡献、合计或趋势。"
        f"\n问题: {question}\n图表: {json.dumps(spec, ensure_ascii=False)}\n"
        f"数据: {json.dumps(sample, ensure_ascii=False, default=str)}"
    )
    if llm_text:
        conclusion = llm_text
        insight = llm_text.split("\n")[0].strip()
    recs = recommend_charts(df)
    anomalies = detect_anomalies(df, spec)
    return {
        **spec,
        "insight": insight,
        "conclusion": conclusion,
        "option": option,
        "recommendations": recs,
        "features": profile_dataframe(df),
        "anomalies": anomalies,
        "style": style or {},
    }


async def chat_dataframe(df: pd.DataFrame, message: str, spec: dict[str, Any]) -> dict[str, Any]:
    updated, tweak_reply = apply_chat_tweak(message, spec)
    if tweak_reply:
        grouped = aggregate_series(df, updated["x_field"], updated["y_field"], updated["aggregation"])
        option = apply_style(
            build_echarts_option(updated["title"], updated["chart_type"], grouped, updated["x_field"], updated.get("y_field") or ""),
            updated.get("style"),
            updated["title"],
        )
        conclusion = local_chart_conclusion(df, updated, grouped)
        return {
            **updated,
            "reply": tweak_reply,
            "insight": updated.get("insight") or local_insight(df, updated, grouped),
            "conclusion": conclusion,
            "option": option,
            "recommendations": recommend_charts(df),
            "anomalies": detect_anomalies(df, updated),
        }
    analyzed = await analyze_dataframe(df, message, updated.get("style"))
    return {**analyzed, "reply": analyzed.get("conclusion") or analyzed["insight"]}

