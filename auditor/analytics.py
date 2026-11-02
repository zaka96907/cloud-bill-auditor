"""Deterministic cost analytics: KPIs, breakdowns, trends, forecast, anomalies."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .parsing import Bill


@dataclass
class Anomaly:
    kind: str              # "daily" (a day spiked) or "line_item" (one row is an outlier)
    label: str             # date or service/resource
    service: str
    cost: float
    expected: float
    score: float           # robust z-score

    @property
    def excess(self) -> float:
        return max(self.cost - self.expected, 0.0)


@dataclass
class Summary:
    total: float
    credits: float
    line_items: int
    services: int
    by_service: pd.DataFrame
    by_region: pd.DataFrame
    by_account: pd.DataFrame
    top_resources: pd.DataFrame
    daily: pd.DataFrame | None
    period_start: pd.Timestamp | None
    period_end: pd.Timestamp | None
    forecast_month_end: float | None
    run_rate_monthly: float | None
    mom_change_pct: float | None
    untagged_cost: float | None
    untagged_pct: float | None
    anomalies: list[Anomaly] = field(default_factory=list)

    @property
    def days(self) -> int | None:
        if self.period_start is None or self.period_end is None:
            return None
        return int((self.period_end - self.period_start).days) + 1


def _robust_z(values: pd.Series) -> pd.Series:
    """Modified z-score using the median absolute deviation.

    Unlike mean+2·std (which a single huge spike inflates and therefore
    hides), MAD is robust to the very outliers we're trying to find."""
    med = values.median()
    mad = (values - med).abs().median()
    if mad == 0 or np.isnan(mad):
        std = values.std()
        if not std or np.isnan(std):
            return pd.Series(0.0, index=values.index)
        return (values - values.mean()) / std
    return 0.6745 * (values - med) / mad


def detect_anomalies(bill: Bill, threshold: float = 3.5, max_items: int = 15) -> list[Anomaly]:
    df = bill.df
    out: list[Anomaly] = []

    # 1) Daily spikes, per service, against a rolling baseline.
    if bill.has_dates:
        daily = (df.dropna(subset=["date"])
                 .groupby(["service", "date"])["cost"].sum().reset_index())
        for service, g in daily.groupby("service"):
            g = g.sort_values("date")
            if len(g) < 7 or g["cost"].sum() <= 0:
                continue
            baseline = g["cost"].rolling(7, min_periods=3).median().shift(1)
            baseline = baseline.fillna(g["cost"].median())
            z = _robust_z(g["cost"])
            for idx in g.index:
                cost = float(g.at[idx, "cost"])
                exp = float(baseline.at[idx])
                if z.at[idx] >= threshold and cost > exp * 1.5 and cost - exp > 1:
                    out.append(Anomaly("daily", g.at[idx, "date"].strftime("%Y-%m-%d"),
                                       str(service), cost, exp, float(z.at[idx])))

    # 2) Individual line items that are extreme outliers.
    pos = df[df["cost"] > 0]
    if len(pos) >= 8:
        z = _robust_z(np.log1p(pos["cost"]))
        for idx in z[z >= threshold].index:
            row = pos.loc[idx]
            label = row["resource"] or row["usage"] or row["service"]
            out.append(Anomaly("line_item", str(label)[:80], str(row["service"]),
                               float(row["cost"]), float(pos["cost"].median()), float(z.at[idx])))

    out.sort(key=lambda a: a.excess, reverse=True)
    return out[:max_items]


def _group(df: pd.DataFrame, col: str, total: float) -> pd.DataFrame:
    g = (df.groupby(col, dropna=False)["cost"].agg(["sum", "count"]).reset_index()
         .rename(columns={"sum": "cost", "count": "line_items"})
         .sort_values("cost", ascending=False))
    g["share_pct"] = (g["cost"] / total * 100).round(2) if total else 0.0
    return g.reset_index(drop=True)


def summarize(bill: Bill, anomaly_threshold: float = 3.5) -> Summary:
    df = bill.df
    total = float(df["cost"].sum())
    credits = float(df.loc[df["cost"] < 0, "cost"].sum())

    by_service = _group(df, "service", total)
    by_region = _group(df, "region", total)
    by_account = _group(df[df["account"] != ""], "account", total) if (df["account"] != "").any() \
        else pd.DataFrame(columns=["account", "cost", "line_items", "share_pct"])

    res = df[df["resource"] != ""]
    top_resources = (res.groupby(["resource", "service"])["cost"].sum().reset_index()
                     .sort_values("cost", ascending=False).head(25).reset_index(drop=True))

    daily = None
    start = end = None
    forecast = run_rate = mom = None
    if bill.has_dates:
        d = df.dropna(subset=["date"])
        daily = d.groupby("date")["cost"].sum().reset_index().sort_values("date")
        start, end = d["date"].min(), d["date"].max()
        n_days = max((end - start).days + 1, 1)
        recent = daily.tail(7)["cost"].mean() if len(daily) >= 3 else total / n_days
        run_rate = float(recent * 30.4)

        # Month-end forecast for the latest month in the bill
        last_month = daily[daily["date"].dt.to_period("M") == end.to_period("M")]
        days_in_month = calendar.monthrange(end.year, end.month)[1]
        remaining = days_in_month - end.day
        forecast = float(last_month["cost"].sum() + max(remaining, 0) * recent)

        # Month-over-month, only if there are two months of data
        monthly = daily.groupby(daily["date"].dt.to_period("M"))["cost"].sum()
        days_in_cur = int(daily[daily['date'].dt.to_period('M') == end.to_period('M')]['date'].nunique())
        if len(monthly) >= 2 and monthly.iloc[-2] > 0 and days_in_cur >= 7:
            # compare equal number of days to be fair
            cur = monthly.iloc[-1]
            prev_days = calendar.monthrange(monthly.index[-2].year, monthly.index[-2].month)[1]
            prev_scaled = monthly.iloc[-2] / prev_days * end.day
            mom = float((cur - prev_scaled) / prev_scaled * 100) if prev_scaled else None

    untagged_cost = untagged_pct = None
    if bill.has_tags:
        tagged = df["tagged"].astype("boolean").fillna(False)
        untagged_cost = float(df.loc[~tagged, "cost"].sum())
        untagged_pct = untagged_cost / total * 100 if total else 0.0

    return Summary(
        total=round(total, 2), credits=round(credits, 2), line_items=len(df),
        services=df["service"].nunique(), by_service=by_service, by_region=by_region,
        by_account=by_account, top_resources=top_resources, daily=daily,
        period_start=start, period_end=end, forecast_month_end=forecast,
        run_rate_monthly=run_rate, mom_change_pct=mom,
        untagged_cost=untagged_cost, untagged_pct=untagged_pct,
        anomalies=detect_anomalies(bill, threshold=anomaly_threshold),
    )
