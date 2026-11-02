import gzip
import io
import json

import pandas as pd
import pytest

from auditor import ai, analytics, parsing, report, rules, samples
from auditor.__main__ import main as cli
from auditor.i18n import AR, EN

END = "2026-10-31"  # fixed so tests are deterministic


def audit(df, lang=EN, **kw):
    bill = parsing.normalize(df)
    s = analytics.summarize(bill)
    return bill, s, rules.run_rules(bill, s, lang, **kw)


@pytest.fixture(scope="module", params=["AWS", "GCP", "Azure"])
def sample(request):
    return request.param, samples.generate(request.param, end=END)


# --- parsing -----------------------------------------------------------------
def test_provider_and_columns_detected(sample):
    provider, df = sample
    bill = parsing.normalize(df)
    assert bill.provider == provider
    cm = bill.columns
    assert cm.cost and cm.service and cm.date and cm.region and cm.resource
    assert bill.has_dates and bill.has_tags
    assert bill.df["cost"].sum() == pytest.approx(df[cm.cost].sum())


def test_legacy_minimal_csv_still_works():
    # The exact sample shipped by v1 of the app.
    df = pd.DataFrame({
        "Service": ["Compute Engine", "Cloud Storage", "BigQuery", "Cloud SQL"],
        "Cost_USD": [1200.50, 450.00, 890.20, 310.00],
        "Usage_Type": ["N1-standard-8 (Unused 80%)", "Standard Storage", "Analysis Queries", "db-custom-4-16000"],
        "Region": ["us-central1", "us-east1", "us-central1", "europe-west1"],
    })
    bill, s, a = audit(df)
    assert bill.columns.cost == "Cost_USD" and bill.columns.service == "Service"
    assert s.total == pytest.approx(2850.70)
    ids = {f.rule_id for f in a.findings}
    assert "underutilized" in ids          # "Unused 80%" -> partial, not 100% idle
    under = next(f for f in a.findings if f.rule_id == "underutilized")
    assert under.savings == pytest.approx(1200.50 * 0.8 * 0.85, rel=1e-3)


def test_money_strings_and_credits():
    df = pd.DataFrame({"service": ["a", "b", "c"], "cost": ["$1,234.50", "(12.00)", " 5 "]})
    bill = parsing.normalize(df)
    assert bill.df["cost"].tolist() == [1234.5, -12.0, 5.0]
    assert any("Negative" in w for w in bill.warnings)


@pytest.mark.parametrize("name,encode", [
    ("bill.csv", lambda b: b),
    ("bill.csv.gz", gzip.compress),
])
def test_read_file_formats(name, encode):
    raw = samples.generate("AWS", end=END).to_csv(index=False).encode()
    df = parsing.read_file(encode(raw), name)
    assert len(df) > 100 and "lineItem/UnblendedCost" in df.columns


def test_semicolon_csv_is_sniffed():
    data = "Service;Cost\nEC2;10.5\nS3;2\n".encode()
    df = parsing.read_file(data, "eu.csv")
    assert list(df.columns) == ["Service", "Cost"]


def test_excel_and_json_roundtrip():
    df = samples.generate("GCP", end=END).head(50)
    xbuf = io.BytesIO(); df.to_excel(xbuf, index=False)
    assert len(parsing.read_file(xbuf.getvalue(), "b.xlsx")) == 50
    js = df.to_json(orient="records").encode()
    assert len(parsing.read_file(js, "b.json")) == 50


def test_column_override():
    df = pd.DataFrame({"svc": ["a", "b"], "cost": [1, 2], "other_cost": [10, 20]})
    bill = parsing.normalize(df, {"cost": "other_cost"})
    assert bill.df["cost"].sum() == 30


def test_empty_bill_raises():
    with pytest.raises(ValueError):
        parsing.normalize(pd.DataFrame())


# --- analytics ---------------------------------------------------------------
def test_log_flood_is_detected_as_anomaly(sample):
    _, df = sample
    bill = parsing.normalize(df)
    s = analytics.summarize(bill)
    daily = [x for x in s.anomalies if x.kind == "daily"]
    assert daily, "the planted 3-day log flood must be flagged"
    assert all(x.cost > x.expected * 3 for x in daily[:3])
    assert s.forecast_month_end and s.run_rate_monthly
    assert s.days == 30


def test_flat_bill_has_no_anomalies():
    dates = pd.date_range("2026-01-01", periods=30)
    df = pd.DataFrame({"date": dates, "service": "EC2", "cost": 10.0})
    s = analytics.summarize(parsing.normalize(df))
    assert s.anomalies == []


# --- rules -------------------------------------------------------------------
def test_savings_are_never_double_counted(sample):
    _, df = sample
    bill, s, a = audit(df)
    assert 0 < a.total_savings < s.total
    assert a.total_savings <= sum(f.savings for f in a.findings) + 1e-6
    assert (a.row_savings <= bill.df["cost"].clip(lower=0) + 1e-9).all()


def test_core_rules_fire_on_samples(sample):
    _, df = sample
    _, _, a = audit(df)
    ids = {f.rule_id for f in a.findings}
    assert {"idle", "underutilized", "dev_247", "prev_gen", "snapshots", "logs", "commitment"} <= ids


def test_idle_resource_is_fully_saved():
    df = pd.DataFrame({"service": ["EBS", "EC2"], "usage": ["volume (unattached)", "m5.large"],
                       "cost": [100.0, 10.0]})
    _, _, a = audit(df)
    idle = next(f for f in a.findings if f.rule_id == "idle")
    assert idle.savings == pytest.approx(100.0)


def test_disabled_rules_are_skipped():
    df = samples.generate("AWS", end=END)
    _, _, a = audit(df, disabled={"commitment", "idle"})
    assert not {"commitment", "idle"} & {f.rule_id for f in a.findings}


def test_arabic_findings():
    _, _, a = audit(samples.generate("Azure", end=END), lang=AR)
    assert any("موارد" in f.title for f in a.findings)
    assert rules.category_label("Storage", AR) == "التخزين"


# --- reports & AI context -----------------------------------------------------
@pytest.mark.parametrize("lang", [EN, AR])
def test_exports(lang):
    bill, s, a = audit(samples.generate("AWS", end=END), lang=lang)
    ai_text = "## ملخص\n- **نص** عربي 🚀\n| a | b |\n|---|---|\n| 1 | 2 |"
    pdf = report.to_pdf(bill, s, a, lang, ai_text)
    assert pdf.startswith(b"%PDF") and len(pdf) > 5000
    xlsx = report.to_excel(bill, s, a, lang, ai_text)
    sheets = pd.ExcelFile(io.BytesIO(xlsx)).sheet_names
    assert {"Overview", "Findings", "By service", "Line items", "AI report"} <= set(sheets)
    md = report.to_markdown(bill, s, a, lang, ai_text)
    assert "$" in md and ("FinOps" in md)


def test_ai_context_is_compact_and_serializable():
    df = samples.generate("AWS", end=END)
    bill, s, a = audit(df)
    ctx = ai.build_context(bill, s, a)
    text = json.dumps(ctx, default=str)
    assert len(ctx["largest_line_items"]) <= 40
    assert len(text) < 60_000  # never ships the whole raw bill
    assert ctx["engine_total_savings_estimate"] == pytest.approx(a.total_savings, abs=0.01)


# --- CLI ---------------------------------------------------------------------
def test_cli(tmp_path, capsys):
    csv = tmp_path / "aws.csv"
    assert cli(["--sample", "aws", "--out", str(csv)]) == 0
    pdf = tmp_path / "r.pdf"
    assert cli([str(csv), "--pdf", str(pdf), "--lang", "ar"]) == 0
    assert pdf.read_bytes().startswith(b"%PDF")
    assert cli([str(csv), "--fail-over", "1"]) == 1
    assert "FinOps" in capsys.readouterr().out
