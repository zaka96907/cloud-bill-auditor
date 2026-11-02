"""Report exports: Markdown, Excel workbook and PDF (with proper Arabic support).

The previous version encoded the PDF text as latin-1, which silently deleted
every Arabic character. Here we embed DejaVu Sans (covers Arabic) and enable
HarfBuzz text shaping so Arabic letters join and run right-to-left.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from .analytics import Summary
from .i18n import tr
from .parsing import Bill
from .rules import AuditResult

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
# Emoji & pictographs DejaVu can't draw (they'd render as empty boxes).
_UNSUPPORTED = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0000FE00-\U0000FE0F\U0000200D\U00002B00-\U00002BFF]"
)

L = {
    "English": {
        "title": "Cloud Bill Audit & FinOps Report", "generated": "Generated",
        "provider": "Provider", "period": "Period", "total": "Total spend",
        "savings": "Potential monthly savings", "forecast": "Month-end forecast",
        "runrate": "Monthly run-rate", "untagged": "Untagged spend",
        "findings": "Savings opportunities", "insights": "Governance & anomalies",
        "services": "Top services", "ai": "AI analysis", "action": "Action",
        "severity": "Severity", "rows": "Line items", "affected": "Affected cost",
        "est": "Est. savings", "service": "Service", "cost": "Cost", "share": "Share",
        "none": "No issues detected by the rules engine.", "finding": "Finding",
        "sev": {"high": "HIGH", "medium": "MEDIUM", "low": "LOW", "info": "INFO"},
    },
    "العربية": {
        "title": "تقرير تدقيق الفاتورة السحابية وخطة FinOps", "generated": "تاريخ الإنشاء",
        "provider": "المزود", "period": "الفترة", "total": "إجمالي الإنفاق",
        "savings": "التوفير الشهري المحتمل", "forecast": "توقع نهاية الشهر",
        "runrate": "معدل الإنفاق الشهري", "untagged": "إنفاق بدون وسوم",
        "findings": "فرص التوفير", "insights": "الحوكمة والانحرافات",
        "services": "أعلى الخدمات تكلفة", "ai": "تحليل الذكاء الاصطناعي", "action": "الإجراء",
        "severity": "الأولوية", "rows": "عدد البنود", "affected": "التكلفة المتأثرة",
        "est": "التوفير المتوقع", "service": "الخدمة", "cost": "التكلفة", "share": "النسبة",
        "none": "لم يكتشف محرك القواعد أي مشاكل.", "finding": "الملاحظة",
        "sev": {"high": "عالية", "medium": "متوسطة", "low": "منخفضة", "info": "معلومة"},
    },
}


def _money(v: float | None) -> str:
    return "—" if v is None else f"${v:,.2f}"


def _period(s: Summary) -> str:
    if s.period_start is None:
        return "—"
    return f"{s.period_start:%Y-%m-%d} → {s.period_end:%Y-%m-%d} ({s.days}d)"


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------
def to_markdown(bill: Bill, s: Summary, audit: AuditResult, lang: str, ai_text: str | None = None) -> str:
    t = L[lang]
    pct = audit.total_savings / s.total * 100 if s.total else 0
    out = [f"# {t['title']}", "",
           f"_{t['generated']}: {datetime.now():%Y-%m-%d %H:%M}_", "",
           f"| | |", "|---|---|",
           f"| {t['provider']} | {bill.provider_label} |",
           f"| {t['period']} | {_period(s)} |",
           f"| {t['total']} | {_money(s.total)} |",
           f"| {t['savings']} | {_money(audit.total_savings)} ({pct:.1f}%) |"]
    if s.forecast_month_end:
        out.append(f"| {t['forecast']} | {_money(s.forecast_month_end)} |")
    if s.untagged_pct is not None:
        out.append(f"| {t['untagged']} | {s.untagged_pct:.1f}% |")

    out += ["", f"## {t['findings']}", ""]
    if audit.findings:
        out += [f"| {t['severity']} | {t['finding']} | {t['rows']} | {t['affected']} | {t['est']} |",
                "|---|---|---|---|---|"]
        for f in audit.findings:
            out.append(f"| {t['sev'][f.severity]} | {f.title} | {f.rows} | {_money(f.affected_cost)} | "
                       f"{_money(f.savings)} |")
        out.append("")
        for f in audit.findings:
            out += [f"### {f.title}", f"- **{t['action']}:** {f.action}"]
            out += [f"- `{e}`" for e in f.examples[:3]]
            out.append("")
    else:
        out.append(t["none"])

    if audit.insights:
        out += ["", f"## {t['insights']}", ""]
        for i in audit.insights:
            out.append(f"- **{i.title}** — {i.action}")

    out += ["", f"## {t['services']}", "", f"| {t['service']} | {t['cost']} | {t['share']} |", "|---|---|---|"]
    for r in s.by_service.head(10).itertuples():
        out.append(f"| {r.service} | {_money(r.cost)} | {r.share_pct:.1f}% |")

    if ai_text:
        out += ["", "---", "", f"## {t['ai']}", "", ai_text.strip()]
    out += ["", "---", "", f"_{disclaimer(lang)}_"]
    return "\n".join(out) + "\n"


def disclaimer(lang: str) -> str:
    return tr("disclaimer", lang).replace("ℹ️", "").strip()


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
def to_excel(bill: Bill, s: Summary, audit: AuditResult, lang: str, ai_text: str | None = None) -> bytes:
    t = L[lang]
    buf = io.BytesIO()
    overview = pd.DataFrame({
        "metric": [t["provider"], t["period"], t["total"], t["savings"], t["forecast"],
                   t["runrate"], t["untagged"], "Disclaimer"],
        "value": [bill.provider_label, _period(s), s.total, round(audit.total_savings, 2),
                  round(s.forecast_month_end, 2) if s.forecast_month_end else None,
                  round(s.run_rate_monthly, 2) if s.run_rate_monthly else None,
                  round(s.untagged_pct, 1) if s.untagged_pct is not None else None,
                  disclaimer(lang)],
    })
    findings = pd.DataFrame([{
        "severity": f.severity, "confidence": f.confidence, "category": f.category,
        "finding": f.title, "line_items": f.rows, "affected_cost": round(f.affected_cost, 2),
        "estimated_savings": round(f.savings, 2), "action": f.action,
        "examples": " | ".join(f.examples),
    } for f in audit.findings + audit.insights])
    lines = bill.df.drop(columns=["text"]).assign(
        estimated_savings=audit.row_savings.round(4), rule=audit.row_rule)
    anomalies = pd.DataFrame([a.__dict__ for a in s.anomalies])

    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        overview.to_excel(xw, sheet_name="Overview", index=False)
        findings.to_excel(xw, sheet_name="Findings", index=False)
        s.by_service.to_excel(xw, sheet_name="By service", index=False)
        s.by_region.to_excel(xw, sheet_name="By region", index=False)
        if not s.by_account.empty:
            s.by_account.to_excel(xw, sheet_name="By account", index=False)
        if s.daily is not None:
            s.daily.to_excel(xw, sheet_name="Daily", index=False)
        if not anomalies.empty:
            anomalies.to_excel(xw, sheet_name="Anomalies", index=False)
        lines.sort_values("estimated_savings", ascending=False).to_excel(xw, sheet_name="Line items", index=False)
        if ai_text:
            pd.DataFrame({"AI report": ai_text.splitlines()}).to_excel(xw, sheet_name="AI report", index=False)

        for ws in xw.book.worksheets:
            ws.freeze_panes = "A2"
            if lang == "العربية":
                ws.sheet_view.rightToLeft = True
            for col in ws.columns:
                width = max((len(str(c.value)) for c in col[:200] if c.value is not None), default=8)
                ws.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 60)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def _clean(text: str) -> str:
    text = _UNSUPPORTED.sub("", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)[*_`](.+?)[*_`](?!\w)", r"\1", text)
    return text.replace("→", "->").strip()


class _PDF:
    def __init__(self, lang: str):
        from fpdf import FPDF

        self.rtl = lang == "العربية"
        pdf = FPDF(format="A4")
        pdf.set_auto_page_break(True, margin=15)
        pdf.set_margins(15, 15, 15)
        regular, bold = FONT_DIR / "DejaVuSans.ttf", FONT_DIR / "DejaVuSans-Bold.ttf"
        self.unicode = regular.exists()
        if self.unicode:
            pdf.add_font("DejaVu", "", str(regular))
            pdf.add_font("DejaVu", "B", str(bold if bold.exists() else regular))
            self.family = "DejaVu"
            try:
                pdf.set_text_shaping(True)
            except Exception:  # uharfbuzz missing: still readable, just not joined
                pass
        else:
            self.family = "Helvetica"
        pdf.add_page()
        self.pdf = pdf

    def _txt(self, text: str) -> str:
        text = _clean(text)
        if not self.unicode:
            text = text.encode("latin-1", "ignore").decode("latin-1")
        return text

    def _align(self, text: str) -> str:
        return "R" if (self.rtl or _ARABIC.search(text)) else "L"

    def heading(self, text: str, size: int = 13):
        text = self._txt(text)
        self.pdf.ln(2)
        self.pdf.set_font(self.family, "B", size)
        self.pdf.set_text_color(30, 58, 138)
        self.pdf.multi_cell(0, size * 0.55, text, align=self._align(text), new_x="LMARGIN", new_y="NEXT")
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.ln(1)

    def para(self, text: str, size: int = 10, bullet: bool = False):
        text = self._txt(text)
        if not text:
            return
        if bullet:
            text = f"{text} •" if self._align(text) == "R" else f"• {text}"
        self.pdf.set_font(self.family, "", size)
        self.pdf.multi_cell(0, 5.5, text, align=self._align(text), new_x="LMARGIN", new_y="NEXT")

    def table(self, rows: list[list[str]]):
        if not rows:
            return
        rows = [[self._txt(c) for c in r] for r in rows]
        if self.rtl:
            rows = [list(reversed(r)) for r in rows]
        self.pdf.set_font(self.family, "", 8.5)
        try:
            from fpdf.fonts import FontFace

            heading = FontFace(emphasis="BOLD", fill_color=(219, 234, 254))
            has_head = any(c.strip() for c in rows[0])
            with self.pdf.table(text_align="CENTER", line_height=5.5, headings_style=heading,
                                first_row_as_headings=has_head,
                                cell_fill_color=(248, 250, 252), cell_fill_mode="ROWS") as tbl:
                for i, r in enumerate(rows):
                    row = tbl.row()
                    if i == 0 and not has_head:
                        continue
                    for c in r:
                        row.cell(c)
        except Exception:
            for r in rows:                                   # graceful fallback
                self.para(" | ".join(r), size=8.5)
        self.pdf.ln(2)

    def markdown(self, md: str):
        table: list[list[str]] = []
        for line in md.splitlines() + [""]:
            s = line.strip()
            if s.startswith("|"):
                cells = [c.strip() for c in s.strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    table.append(cells)
                continue
            if table:
                width = max(len(r) for r in table)
                self.table([r + [""] * (width - len(r)) for r in table])
                table = []
            if not s or s == "---":
                self.pdf.ln(1.5)
            elif s.startswith("#"):
                level = len(s) - len(s.lstrip("#"))
                self.heading(s.lstrip("#").strip(), size={1: 16, 2: 13, 3: 11.5}.get(level, 11))
            elif re.match(r"^([-*+]|\d+[.)])\s+", s):
                self.para(re.sub(r"^([-*+])\s+", "", s), bullet=s[0] in "-*+")
            else:
                self.para(s)

    def output(self) -> bytes:
        return bytes(self.pdf.output())


def to_pdf(bill: Bill, s: Summary, audit: AuditResult, lang: str, ai_text: str | None = None) -> bytes:
    doc = _PDF(lang)
    doc.markdown(to_markdown(bill, s, audit, lang, ai_text))
    return doc.output()
