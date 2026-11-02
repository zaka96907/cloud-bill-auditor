"""Gemini integration: an AI-written FinOps report and a chat about the bill.

Only a compact, pre-aggregated context is sent (never the full raw bill),
which keeps requests fast, cheap and within token limits even for bills
with hundreds of thousands of line items.
"""

from __future__ import annotations

import json
import time
from typing import Iterator

from .analytics import Summary
from .parsing import Bill
from .rules import AuditResult

MODELS = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"]
DEFAULT_MODEL = MODELS[0]

SYSTEM_PROMPT = """You are a Senior Cloud FinOps practitioner (FinOps Certified Practitioner, \
AWS/GCP/Azure). You audit cloud bills and produce precise, actionable, prioritized advice.
Rules:
- Base every number on the provided context. Never invent services, resources or prices.
- The deterministic engine already estimated savings; reuse those figures, and clearly mark \
anything you add as an estimate.
- Be concrete: name the resource/service, the exact action, the expected $ impact and the effort.
- Use Markdown with headings, short bullet points and tables where helpful.
- Write entirely in {language}. Keep technical terms (e.g. Savings Plans, gp3) in English."""

REPORT_PROMPT = """Write the FinOps audit report for this cloud bill with exactly these sections:

1. Executive summary (3–5 bullets: spend, period, provider, biggest issues, total savings potential)
2. Savings opportunities table (Opportunity | Monthly savings $ | Effort | Risk | Priority)
3. Prioritized action plan
   - Quick wins (this week)
   - Medium term (this month: rightsizing, commitments, scheduling)
   - Governance (tagging, budgets, anomaly alerts, ownership)
4. Anomalies & risks to investigate
5. 30/60/90-day roadmap

Context (JSON):
{context}"""


def build_context(bill: Bill, s: Summary, audit: AuditResult, max_rows: int = 40) -> dict:
    df = bill.df
    top_lines = (df.assign(savings=audit.row_savings, rule=audit.row_rule)
                 .sort_values("cost", ascending=False).head(max_rows))
    ctx = {
        "provider": bill.provider_label,
        "currency": "USD",
        "period": {
            "start": s.period_start.strftime("%Y-%m-%d") if s.period_start is not None else None,
            "end": s.period_end.strftime("%Y-%m-%d") if s.period_end is not None else None,
            "days": s.days,
        },
        "total_spend": round(s.total, 2),
        "credits_refunds": s.credits,
        "line_items": s.line_items,
        "monthly_run_rate": round(s.run_rate_monthly, 2) if s.run_rate_monthly else None,
        "forecast_month_end": round(s.forecast_month_end, 2) if s.forecast_month_end else None,
        "month_over_month_pct": round(s.mom_change_pct, 1) if s.mom_change_pct is not None else None,
        "untagged_spend_pct": round(s.untagged_pct, 1) if s.untagged_pct is not None else None,
        "top_services": s.by_service.head(12)[["service", "cost", "share_pct"]].round(2).to_dict("records"),
        "top_regions": s.by_region.head(8)[["region", "cost", "share_pct"]].round(2).to_dict("records"),
        "top_accounts_projects": (s.by_account.head(8)[["account", "cost"]].round(2).to_dict("records")
                                  if not s.by_account.empty else []),
        "top_resources": s.top_resources.head(15).round(2).to_dict("records"),
        "engine_total_savings_estimate": round(audit.total_savings, 2),
        "engine_findings": [
            {"title": f.title, "category": f.category, "severity": f.severity,
             "confidence": f.confidence, "line_items": f.rows,
             "affected_cost": round(f.affected_cost, 2), "estimated_savings": round(f.savings, 2),
             "examples": f.examples[:3], "recommended_action": f.action}
            for f in audit.findings
        ],
        "governance_insights": [i.title for i in audit.insights],
        "anomalies": [
            {"type": a.kind, "when_or_what": a.label, "service": a.service,
             "cost": round(a.cost, 2), "expected": round(a.expected, 2)}
            for a in s.anomalies
        ],
        "largest_line_items": [
            {"service": r.service, "resource": r.resource[:80], "usage": r.usage[:80],
             "region": r.region, "cost": round(r.cost, 2), "est_savings": round(r.savings, 2),
             "rule": r.rule}
            for r in top_lines.itertuples()
        ],
    }
    return ctx


def _client(api_key: str):
    from google import genai
    return genai.Client(api_key=api_key)


def _config(language: str, temperature: float = 0.3):
    from google.genai import types
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT.format(language=language),
        temperature=temperature,
    )


def _retry(fn, attempts: int = 3):
    """Retry transient errors (503 overloaded / 429 rate limit) with backoff."""
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - SDK raises several error types
            last = e
            msg = str(e)
            if not any(code in msg for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "overloaded")):
                raise
            time.sleep(2 ** i * 2)
    raise last


def stream_report(api_key: str, context: dict, language: str, model: str = DEFAULT_MODEL) -> Iterator[str]:
    client = _client(api_key)
    prompt = REPORT_PROMPT.format(context=json.dumps(context, ensure_ascii=False, default=str))
    stream = _retry(lambda: client.models.generate_content_stream(
        model=model, contents=prompt, config=_config(language)))
    for chunk in stream:
        if getattr(chunk, "text", None):
            yield chunk.text


def stream_chat(api_key: str, context: dict, history: list[dict], question: str,
                language: str, model: str = DEFAULT_MODEL) -> Iterator[str]:
    """``history`` is a list of {"role": "user"|"assistant", "content": str}."""
    from google.genai import types

    client = _client(api_key)
    grounding = ("Answer questions about this cloud bill. Use only this context; if the answer "
                 "is not in it, say so and suggest which report/column would contain it.\n\n"
                 + json.dumps(context, ensure_ascii=False, default=str))
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=grounding)]),
                types.Content(role="model", parts=[types.Part.from_text(text="Understood.")])]
    for m in history[-10:]:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))

    stream = _retry(lambda: client.models.generate_content_stream(
        model=model, contents=contents, config=_config(language, temperature=0.4)))
    for chunk in stream:
        if getattr(chunk, "text", None):
            yield chunk.text
