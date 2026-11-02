"""Plotly figures. Every function returns a figure (or None when not applicable)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .analytics import Summary
from .rules import AuditResult, category_label

PALETTE = ["#2563eb", "#0d9488", "#f59e0b", "#e11d48", "#7c3aed", "#0891b2",
           "#65a30d", "#db2777", "#ea580c", "#4f46e5", "#64748b"]
SAVINGS_COLOR = "#16a34a"
ANOMALY_COLOR = "#dc2626"


def _layout(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.01, font=dict(size=15)),
        height=height, margin=dict(t=50, b=20, l=10, r=10),
        legend=dict(orientation="h", y=-0.15),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Tahoma, sans-serif"),
    )
    return fig


def _top_n(df: pd.DataFrame, label: str, n: int, other: str) -> pd.DataFrame:
    if len(df) <= n:
        return df[[label, "cost"]]
    head = df.head(n)[[label, "cost"]]
    rest = pd.DataFrame({label: [other], "cost": [df["cost"].iloc[n:].sum()]})
    return pd.concat([head, rest], ignore_index=True)


def service_donut(s: Summary, title: str, other: str = "Other") -> go.Figure:
    data = _top_n(s.by_service[s.by_service["cost"] > 0], "service", 8, other)
    fig = px.pie(data, values="cost", names="service", hole=0.55, color_discrete_sequence=PALETTE)
    fig.update_traces(textposition="inside", textinfo="percent",
                      hovertemplate="%{label}<br>$%{value:,.2f} (%{percent})<extra></extra>")
    return _layout(fig, title)


def top_services_bar(s: Summary, title: str, n: int = 10) -> go.Figure:
    data = s.by_service.head(n).iloc[::-1]
    fig = go.Figure(go.Bar(x=data["cost"], y=data["service"], orientation="h",
                           marker_color=PALETTE[0], text=[f"${v:,.0f}" for v in data["cost"]],
                           textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}<br>$%{x:,.2f}<extra></extra>"))
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,.15)", tickprefix="$")
    return _layout(fig, title, height=max(320, 34 * len(data) + 90))


def daily_trend(s: Summary, title: str, labels: dict) -> go.Figure | None:
    if s.daily is None or len(s.daily) < 2:
        return None
    d = s.daily
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["date"], y=d["cost"], mode="lines", name=labels["daily"],
                             line=dict(color=PALETTE[0], width=2.5), fill="tozeroy",
                             fillcolor="rgba(37,99,235,.08)",
                             hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.2f}<extra></extra>"))
    ma = d["cost"].rolling(7, min_periods=1).mean()
    fig.add_trace(go.Scatter(x=d["date"], y=ma, mode="lines", name=labels["avg7"],
                             line=dict(color="#94a3b8", width=1.5, dash="dot")))
    daily_anoms = [a for a in s.anomalies if a.kind == "daily"]
    if daily_anoms:
        dates = pd.to_datetime(sorted({a.label for a in daily_anoms}))
        pts = d[d["date"].isin(dates)]
        fig.add_trace(go.Scatter(x=pts["date"], y=pts["cost"], mode="markers", name=labels["anomaly"],
                                 marker=dict(color=ANOMALY_COLOR, size=11, symbol="diamond",
                                             line=dict(color="white", width=1.5))))
    fig.update_yaxes(tickprefix="$", gridcolor="rgba(128,128,128,.15)")
    return _layout(fig, title)


def service_trend(bill_df: pd.DataFrame, title: str, n: int = 6, other: str = "Other") -> go.Figure | None:
    d = bill_df.dropna(subset=["date"])
    if d.empty or d["date"].nunique() < 2:
        return None
    top = d.groupby("service")["cost"].sum().nlargest(n).index
    d = d.assign(service=d["service"].where(d["service"].isin(top), other))
    g = d.groupby(["date", "service"])["cost"].sum().reset_index()
    fig = px.area(g, x="date", y="cost", color="service", color_discrete_sequence=PALETTE)
    fig.update_yaxes(tickprefix="$", gridcolor="rgba(128,128,128,.15)")
    return _layout(fig, title)


def region_bar(s: Summary, title: str) -> go.Figure | None:
    data = s.by_region[s.by_region["cost"] > 0].head(12)
    if len(data) < 2:
        return None
    fig = px.bar(data, x="region", y="cost", color_discrete_sequence=[PALETTE[1]],
                 text=[f"${v:,.0f}" for v in data["cost"]])
    fig.update_yaxes(tickprefix="$", gridcolor="rgba(128,128,128,.15)")
    fig.update_traces(textposition="outside", cliponaxis=False)
    return _layout(fig, title)


def savings_waterfall(total: float, audit: AuditResult, title: str, labels: dict,
                      lang: str = "English") -> go.Figure | None:
    cats = audit.savings_by_category()
    if cats.empty:
        return None
    x = [labels["current"]] + [category_label(c, lang) for c in cats["category"]] + [labels["optimized"]]
    y = [total] + [-v for v in cats["savings"]] + [0]
    fig = go.Figure(go.Waterfall(
        x=x, y=y, measure=["absolute"] + ["relative"] * len(cats) + ["total"],
        text=[f"${abs(v):,.0f}" for v in y[:-1]] + [f"${total - audit.total_savings:,.0f}"],
        textposition="outside", cliponaxis=False,
        decreasing=dict(marker=dict(color=SAVINGS_COLOR)),
        totals=dict(marker=dict(color=PALETTE[0])),
        increasing=dict(marker=dict(color=PALETTE[0])),
        connector=dict(line=dict(color="rgba(128,128,128,.4)")),
    ))
    fig.update_yaxes(tickprefix="$", gridcolor="rgba(128,128,128,.15)")
    return _layout(fig, title, height=420)


def treemap(bill_df: pd.DataFrame, title: str) -> go.Figure | None:
    d = bill_df[bill_df["cost"] > 0].copy()
    if d.empty:
        return None
    d["resource"] = d["resource"].replace("", "—").str.slice(0, 50)
    g = d.groupby(["service", "resource"])["cost"].sum().reset_index()
    # keep the treemap readable on large bills
    g = g.sort_values("cost", ascending=False).head(150)
    fig = px.treemap(g, path=[px.Constant("Total"), "service", "resource"], values="cost",
                     color="cost", color_continuous_scale="Blues")
    fig.update_traces(hovertemplate="%{label}<br>$%{value:,.2f}<extra></extra>")
    fig.update_layout(coloraxis_showscale=False)
    return _layout(fig, title, height=480)


def budget_gauge(value: float, budget: float, title: str) -> go.Figure:
    pct = value / budget * 100 if budget else 0
    color = SAVINGS_COLOR if pct < 80 else ("#f59e0b" if pct < 100 else ANOMALY_COLOR)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=value,
        number=dict(prefix="$", valueformat=",.0f"),
        delta=dict(reference=budget, valueformat=",.0f", prefix="$",
                   increasing=dict(color=ANOMALY_COLOR), decreasing=dict(color=SAVINGS_COLOR)),
        gauge=dict(axis=dict(range=[0, max(budget, value) * 1.2]),
                   bar=dict(color=color),
                   threshold=dict(line=dict(color="#111827", width=3), value=budget)),
    ))
    return _layout(fig, title, height=300)
