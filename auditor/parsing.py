"""Load cloud bills in many formats and normalize them into one schema.

Every supported export (AWS CUR / Cost Explorer, GCP billing export,
Azure cost details, or any generic CSV) is mapped onto these columns:

    date, service, cost, region, resource, usage, account, tagged, text

so the rest of the app never has to care which provider a bill came from.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import pandas as pd

# ---------------------------------------------------------------------------
# Column-name candidates, in priority order. Names are compared after
# ``_key()`` normalisation (lower-case, alphanumerics only), so
# "lineItem/UnblendedCost", "line_item_unblended_cost" and
# "LineItem UnblendedCost" all become "lineitemunblendedcost".
# ---------------------------------------------------------------------------
COST_CANDIDATES = [
    "lineitemunblendedcost", "unblendedcost", "lineitemnetunblendedcost",
    "netunblendedcost", "costinbillingcurrency", "costinusd", "pretaxcost",
    "costusd", "cost", "totalcost", "amount", "lineitemblendedcost",
    "blendedcost", "extendedcost", "billedcost", "effectivecost", "charge",
    "charges", "price",
]
SERVICE_CANDIDATES = [
    "productproductname", "productname", "lineitemproductcode",
    "servicedescription", "servicename", "service", "metercategory",
    "consumedservice", "productcode", "product", "servicecategory",
]
DATE_CANDIDATES = [
    "lineitemusagestartdate", "usagestartdate", "usagestarttime",
    "usagedatetime", "usagedate", "date", "day", "chargeperiodstart",
    "billingperiodstartdate", "starttime", "timestamp", "period",
]
REGION_CANDIDATES = [
    "productregion", "productregioncode", "region", "locationregion",
    "resourcelocation", "location", "regionname", "lineitemavailabilityzone",
    "availabilityzone", "zone",
]
RESOURCE_CANDIDATES = [
    "lineitemresourceid", "resourceid", "instanceid", "resourcename",
    "resource", "resourcename", "name",
]
USAGE_CANDIDATES = [
    "lineitemusagetype", "usagetype", "skudescription", "metername",
    "metersubcategory", "lineitemlineitemdescription", "description",
    "usage", "sku", "instancetype", "productinstancetype",
]
ACCOUNT_CANDIDATES = [
    "lineitemusageaccountid", "usageaccountid", "linkedaccount",
    "accountid", "projectid", "projectname", "project", "subscriptionname",
    "subscriptionid", "resourcegroup", "billingaccountid",
]
TAG_PREFIXES = ("resourcetags", "tags", "labels", "tag", "label")

PROVIDER_AWS = "AWS"
PROVIDER_GCP = "GCP"
PROVIDER_AZURE = "Azure"
PROVIDER_GENERIC = "Generic"

PROVIDER_LABELS = {
    PROVIDER_AWS: "AWS (Amazon Web Services)",
    PROVIDER_GCP: "Google Cloud Platform (GCP)",
    PROVIDER_AZURE: "Microsoft Azure",
    PROVIDER_GENERIC: "Generic / Unknown provider",
}

SUPPORTED_EXTENSIONS = ["csv", "gz", "zip", "xlsx", "xls", "json", "parquet", "tsv", "txt"]


def _is_text(series: pd.Series) -> bool:
    """True for object *and* the pandas>=3 string dtype."""
    return (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)) \
        and not pd.api.types.is_numeric_dtype(series)


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


@dataclass
class ColumnMap:
    cost: str | None = None
    service: str | None = None
    date: str | None = None
    region: str | None = None
    resource: str | None = None
    usage: str | None = None
    account: str | None = None
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v}


@dataclass
class Bill:
    """A normalized bill plus metadata about where it came from."""

    df: pd.DataFrame          # normalized frame (see module docstring)
    raw: pd.DataFrame         # original frame, untouched
    provider: str
    columns: ColumnMap
    warnings: list[str] = field(default_factory=list)

    @property
    def provider_label(self) -> str:
        return PROVIDER_LABELS.get(self.provider, self.provider)

    @property
    def has_dates(self) -> bool:
        return self.df["date"].notna().any()

    @property
    def has_tags(self) -> bool:
        return bool(self.columns.tags)


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------
def read_file(data: bytes, filename: str) -> pd.DataFrame:
    """Read a bill from raw bytes. Supports csv/tsv (optionally gz/zip),
    xlsx/xls, json (records or lines) and parquet."""
    name = filename.lower()
    buf = io.BytesIO(data)

    if name.endswith(".parquet"):
        return pd.read_parquet(buf)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(buf)
    if name.endswith(".json"):
        try:
            return pd.json_normalize(pd.read_json(buf).to_dict(orient="records"))
        except ValueError:
            buf.seek(0)
            return pd.read_json(buf, lines=True)

    compression = "infer"
    if name.endswith(".gz"):
        compression = "gzip"
    elif name.endswith(".zip"):
        compression = "zip"
    inner = re.sub(r"\.(gz|zip)$", "", name)
    sep = "\t" if inner.endswith(".tsv") else ","
    df = pd.read_csv(buf, compression=compression, sep=sep, low_memory=False, on_bad_lines="skip")
    if df.shape[1] == 1:
        # Probably ';' or tab separated (common in European Excel exports) — sniff it.
        buf.seek(0)
        df = pd.read_csv(buf, compression=compression, sep=None, engine="python", on_bad_lines="skip")
    return df


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------
def detect_provider(columns: list[str]) -> str:
    keys = [_key(c) for c in columns]
    joined = " ".join(keys)
    aws = sum(k.startswith(("lineitem", "product", "resourcetags", "pricing", "bill"))
              for k in keys) + ("unblendedcost" in joined) * 3
    gcp = sum(k.startswith(("service", "sku", "project", "labels", "credits", "invoice"))
              for k in keys) + ("skudescription" in joined or "servicedescription" in joined) * 3
    azure = sum(k.startswith(("meter", "subscription", "resourcegroup", "consumedservice",
                              "costinbillingcurrency", "pretaxcost"))
                for k in keys) + ("metercategory" in joined or "costinbillingcurrency" in joined) * 3
    scores = {PROVIDER_AWS: aws, PROVIDER_GCP: gcp, PROVIDER_AZURE: azure}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else PROVIDER_GENERIC


def _pick(columns: list[str], candidates: list[str], exclude: set[str] = frozenset()) -> str | None:
    keyed = {c: _key(c) for c in columns if c not in exclude}
    for cand in candidates:                       # exact match first
        for col, k in keyed.items():
            if k == cand:
                return col
    for cand in candidates:                       # then suffix match ("x/cost")
        for col, k in keyed.items():
            if k.endswith(cand) and len(cand) >= 4:
                return col
    return None


def _guess_cost_column(df: pd.DataFrame, exclude: set[str]) -> str | None:
    """Fall back to the numeric column with the most 'money-like' values."""
    best, best_score = None, -1.0
    for col in df.columns:
        if col in exclude:
            continue
        k = _key(col)
        if any(bad in k for bad in ("quantity", "usageamount", "rate", "id", "hours", "count")):
            continue
        num = pd.to_numeric(df[col], errors="coerce")
        ratio = num.notna().mean()
        if ratio < 0.8:
            continue
        score = ratio + (1.0 if "cost" in k or "amount" in k else 0.0)
        if score > best_score:
            best, best_score = col, score
    return best


def map_columns(df: pd.DataFrame) -> ColumnMap:
    cols = list(df.columns)
    cm = ColumnMap()
    cm.cost = _pick(cols, COST_CANDIDATES)
    if cm.cost is None:
        # anything containing "cost" that is numeric
        for c in cols:
            if "cost" in _key(c) and pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.5:
                cm.cost = c
                break
    if cm.cost is None:
        cm.cost = _guess_cost_column(df, set())
    used = {cm.cost}
    cm.service = _pick(cols, SERVICE_CANDIDATES, used); used.add(cm.service)
    cm.date = _pick(cols, DATE_CANDIDATES, used); used.add(cm.date)
    cm.region = _pick(cols, REGION_CANDIDATES, used); used.add(cm.region)
    cm.resource = _pick(cols, RESOURCE_CANDIDATES, used); used.add(cm.resource)
    cm.usage = _pick(cols, USAGE_CANDIDATES, used); used.add(cm.usage)
    cm.account = _pick(cols, ACCOUNT_CANDIDATES, used)
    cm.tags = [c for c in cols if _key(c).startswith(TAG_PREFIXES)]

    if cm.service is None:
        # first text column that is not otherwise used
        for c in cols:
            if c not in used and _is_text(df[c]):
                cm.service = c
                break
    return cm


def _parse_money(series: pd.Series) -> pd.Series:
    if _is_text(series):
        series = (series.astype(str)
                  .str.replace(r"[^\d,.\-()]", "", regex=True)
                  .str.replace(r"^\((.*)\)$", r"-\1", regex=True)   # (12.5) -> -12.5
                  .str.replace(",", "", regex=False))
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _tag_present(row_values) -> bool:
    for v in row_values:
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() not in ("nan", "none", "{}", "[]", "null", ""):
            return True
    return False


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def normalize(raw: pd.DataFrame, overrides: dict | None = None) -> Bill:
    """Turn any bill DataFrame into a :class:`Bill`.

    ``overrides`` lets the user correct the auto-detected mapping, e.g.
    ``{"cost": "MyCostColumn"}``.
    """
    if raw is None or raw.empty:
        raise ValueError("The bill is empty.")

    raw = raw.copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    raw = raw.dropna(how="all")

    cm = map_columns(raw)
    for k, v in (overrides or {}).items():
        if v and v in raw.columns and hasattr(cm, k):
            setattr(cm, k, v)

    warnings: list[str] = []
    if cm.cost is None:
        raise ValueError("Could not find a cost column in this file.")

    n = len(raw)
    df = pd.DataFrame(index=raw.index)
    df["cost"] = _parse_money(raw[cm.cost])
    df["service"] = (raw[cm.service].astype(str).str.strip().replace({"": "Unknown", "nan": "Unknown"})
                     if cm.service else "Unknown")

    if cm.date:
        dates = pd.to_datetime(raw[cm.date], errors="coerce", utc=True)
        if dates.notna().mean() < 0.5:
            warnings.append(f"Date column '{cm.date}' could not be parsed reliably.")
        df["date"] = dates.dt.tz_convert(None).dt.normalize()
    else:
        df["date"] = pd.NaT

    def _text(col):
        return raw[col].astype(str).replace({"nan": ""}) if col else pd.Series([""] * n, index=raw.index)

    df["region"] = _text(cm.region).replace({"": "global"})
    df["resource"] = _text(cm.resource)
    df["usage"] = _text(cm.usage)
    df["account"] = _text(cm.account)

    if cm.tags:
        df["tagged"] = raw[cm.tags].apply(lambda r: _tag_present(r.values), axis=1)
    else:
        df["tagged"] = pd.NA

    # One lower-cased blob per row that the rules engine pattern-matches on.
    text_cols = [c for c in raw.columns if _is_text(raw[c])]
    if text_cols:
        df["text"] = (raw[text_cols].astype(str).fillna("")
                      .agg(" ".join, axis=1).str.lower())
    else:
        df["text"] = ""

    if (df["cost"] < 0).any():
        warnings.append("Negative line items (credits/refunds) were found and kept as-is.")

    return Bill(df=df.reset_index(drop=True), raw=raw.reset_index(drop=True),
                provider=detect_provider(list(raw.columns)), columns=cm, warnings=warnings)


def load_bill(data: bytes, filename: str, overrides: dict | None = None) -> Bill:
    return normalize(read_file(data, filename), overrides)
