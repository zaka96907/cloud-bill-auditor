"""Cloud Bill Auditor — Streamlit UI.

All analysis logic lives in the ``auditor`` package; this file only renders it.
Run with:  streamlit run app.py
"""

from __future__ import annotations

import hashlib
import json

import pandas as pd
import streamlit as st

from auditor import __version__, ai, analytics, charts, licensing, parsing, report, rules, samples
from auditor.i18n import AR, LANGUAGES, tr

st.set_page_config(page_title="Cloud Bill Auditor", page_icon="🕵️", layout="wide",
                   initial_sidebar_state="expanded")

SEV_ICON = {"high": "🔴", "medium": "🟠", "low": "🟡", "info": "🔵"}
MAP_FIELDS = ["cost", "service", "date", "region", "resource", "usage", "account"]
REPO_URL = "https://github.com/zaka96907/cloud-bill-auditor/blob/main"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def money(v: float | None, decimals: int = 0) -> str:
    return "—" if v is None else f"${v:,.{decimals}f}"


def _all_secrets() -> dict:
    try:
        return dict(st.secrets)
    except Exception:  # no secrets.toml
        return {}


def analyze(files: tuple, overrides: dict, lang: str, disabled: tuple, threshold: float):
    frames = [parsing.read_file(data, name) for name, data in files]
    raw = pd.concat(frames, ignore_index=True, sort=False) if len(frames) > 1 else frames[0]
    bill = parsing.normalize(raw, overrides)
    summary = analytics.summarize(bill, anomaly_threshold=threshold)
    audit = rules.run_rules(bill, summary, lang, disabled=set(disabled))
    return bill, summary, audit


def session_cached(slot: str, key: str, fn):
    """Cache a result in *this user's* session only.

    Deliberately not ``st.cache_data``: that cache is shared by every visitor
    of the server, so bills would stay in memory across users."""
    entry = st.session_state.get(slot)
    if entry is None or entry[0] != key:
        entry = (key, fn())
        st.session_state[slot] = entry
    return entry[1]


def clear_session():
    for k in ("files", "_analysis", "_exports"):
        st.session_state.pop(k, None)
    st.session_state["ai_text"] = {}
    st.session_state["chat"] = {}
    # A new key gives a fresh, empty uploader widget (and drops the old file from memory).
    st.session_state["uploader_gen"] = st.session_state.get("uploader_gen", 0) + 1


def upgrade_cta(lang: str, where=st):
    if cfg.buy_url:
        label = tr("buy_btn", lang) + (f" — {cfg.price_label}" if cfg.price_label else "")
        where.link_button(label, cfg.buy_url, type="primary")


cfg = licensing.Config.from_mapping(_all_secrets())


def ai_error_message(e: Exception, lang: str) -> str:
    msg = str(e)
    if any(c in msg for c in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "overloaded")):
        return tr("ai_busy", lang)
    if any(c in msg for c in ("API_KEY_INVALID", "API key not valid", "PERMISSION_DENIED", "401", "403")):
        return tr("ai_bad_key", lang)
    return f"{tr('ai_error', lang)}: {msg[:300]}"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    # ?lang=ar in the URL opens the app in Arabic (handy for sharing links).
    default_lang = 1 if st.query_params.get("lang", "").lower() in ("ar", "arabic") else 0
    lang = st.selectbox("🌐 Language / اللغة", LANGUAGES, index=default_lang, key="lang")

    plan = licensing.PRO
    if cfg.monetized:
        st.subheader(f"⭐ {tr('sb_plan', lang)}")
        code = st.text_input(tr("code_label", lang), type="password", key="access_code")
        plan = licensing.plan_for(code, cfg)
        if plan == licensing.PRO:
            st.success(tr("plan_pro", lang))
        else:
            if code:
                st.error(tr("code_bad", lang))
            st.info(f"**{tr('plan_free', lang)}** — {tr('pro_perks', lang)}")
            upgrade_cta(lang)
    is_pro = plan == licensing.PRO

    st.subheader(f"🤖 {tr('sb_ai', lang)}")
    user_key = st.text_input(tr("api_label", lang), type="password", help=tr("api_help", lang))
    owner_key = str(_all_secrets().get("GEMINI_API_KEY", "") or "")
    # The owner's key (from secrets) is a paid perk and rate-limited per session;
    # a visitor's own key is always allowed and unlimited.
    using_owner_key = not user_key and bool(owner_key) and is_pro
    api_key = user_key or (owner_key if using_owner_key else "")
    st.markdown(f"[{tr('api_link', lang)} ↗](https://aistudio.google.com/app/apikey)")
    model = st.selectbox(tr("model_label", lang), ai.MODELS, index=0)

    st.subheader(f"⚙️ {tr('sb_settings', lang)}")
    budget = st.number_input(tr("budget_label", lang), min_value=0.0, value=0.0, step=100.0)
    sensitivity = st.slider(tr("sensitivity_label", lang), 2.0, 6.0, 3.5, 0.5,
                            help=tr("sensitivity_help", lang))
    rule_names = {r.id: r.title[lang] for r in rules.RULES}
    with st.expander(tr("rules_label", lang)):
        active = [rid for rid, name in rule_names.items() if st.checkbox(name, True, key=f"rule_{rid}")]
    disabled = tuple(sorted(set(rule_names) - set(active)))

    st.caption(tr("privacy", lang))
    st.caption(f"v{__version__}")

# Right-to-left layout for Arabic (charts, tables and code stay LTR).
if lang == AR:
    st.markdown("""
<style>
[data-testid="stMain"], [data-testid="stSidebar"], [data-testid="stChatMessage"] {direction: rtl; text-align: right;}
[data-testid="stMetric"], .stMarkdown, .stAlert, label {direction: rtl; text-align: right;}
.js-plotly-plot, [data-testid="stDataFrame"], code, pre, [data-baseweb="slider"] {direction: ltr; text-align: left;}
</style>""", unsafe_allow_html=True)

st.markdown("""
<style>
[data-testid="stMetric"] {background: rgba(37,99,235,.04); border-radius: 12px; padding: 12px 16px;}
[data-testid="stMetricValue"] {font-size: 1.7rem;}
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header & input
# ---------------------------------------------------------------------------
st.title(f"🕵️ {tr('app_title', lang)}")
st.caption(tr("app_subtitle", lang))

ss = st.session_state
ss.setdefault("files", None)        # tuple[(name, bytes)]
ss.setdefault("ai_text", {})        # {analysis_key: text}
ss.setdefault("chat", {})           # {analysis_key: [messages]}
ss.setdefault("ai_used", 0)         # AI requests made with the owner's key this session

tab_up, tab_sample = st.tabs([tr("tab_upload", lang), tr("tab_sample", lang)])
with tab_up:
    uploads = st.file_uploader(tr("uploader_label", lang), type=parsing.SUPPORTED_EXTENSIONS,
                               accept_multiple_files=True, help=tr("uploader_help", lang),
                               key=f"uploader_{ss.get('uploader_gen', 0)}")
    if uploads:
        files = tuple((u.name, u.getvalue()) for u in uploads)
        if files != ss.files:
            ss.files = files
with tab_sample:
    c1, c2 = st.columns([1, 2])
    provider = c1.radio(tr("sample_provider", lang), ["AWS", "GCP", "Azure"], horizontal=True)
    if c2.button(tr("sample_btn", lang), type="primary"):
        csv = samples.generate(provider).to_csv(index=False).encode()
        ss.files = ((f"sample_{provider.lower()}_bill.csv", csv),)
        st.success(tr("sample_ok", lang))

if not ss.files:
    st.info(tr("empty_state", lang))
    st.divider()
    st.subheader(tr("b2b_header", lang))
    st.write(tr("b2b_text", lang))
    st.info(f"{tr('b2b_contact', lang)} {cfg.contact_email}")
    st.stop()

names = ", ".join(n for n, _ in ss.files)
overrides = {f: ss.get(f"map_{f}") for f in MAP_FIELDS if ss.get(f"map_{f}") not in (None, tr("auto", lang))}
digest = hashlib.sha1(b"".join(d for _, d in ss.files)).hexdigest()[:12]
analysis_key = f"{digest}|{json.dumps(overrides, sort_keys=True)}|{lang}|{disabled}|{sensitivity}"

try:
    with st.spinner("…"):
        bill, summary, audit = session_cached(
            "_analysis", analysis_key,
            lambda: analyze(ss.files, overrides, lang, disabled, sensitivity))
except Exception as e:  # noqa: BLE001
    st.error(f"{tr('error_read', lang)} ({names}): {e}")
    if st.button(tr("clear", lang)):
        clear_session()
        st.rerun()
    st.stop()

if not is_pro and summary.line_items > cfg.free_max_line_items:
    st.warning(tr("locked_size", lang, n=cfg.free_max_line_items, m=summary.line_items))
    upgrade_cta(lang)
    if st.button(tr("clear", lang)):
        clear_session()
        st.rerun()
    st.stop()

top = st.columns([4, 1])
top[0].markdown(f"**{tr('provider', lang)}:** {bill.provider_label} · `{names}`")
if top[1].button(f"🗑️ {tr('clear', lang)}", width="stretch"):
    clear_session()
    st.rerun()

with st.expander(tr("mapping", lang)):
    st.caption(tr("mapping_help", lang))
    cols = [tr("auto", lang)] + list(bill.raw.columns)
    detected = bill.columns.as_dict()
    mcols = st.columns(len(MAP_FIELDS))
    for i, f in enumerate(MAP_FIELDS):
        mcols[i].selectbox(f"{f} → {detected.get(f, '—')}", cols, key=f"map_{f}")
    if bill.columns.tags:
        st.caption("Tags: " + ", ".join(bill.columns.tags))

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
s, a = summary, audit
sav_pct = a.total_savings / s.total * 100 if s.total else 0
k = st.columns(6)
k[0].metric(tr("kpi_total", lang), money(s.total),
            f"{s.mom_change_pct:+.1f}% {tr('vs_prev', lang)}" if s.mom_change_pct is not None else None,
            delta_color="inverse")
k[1].metric(tr("kpi_savings", lang), money(a.total_savings), f"{sav_pct:.1f}% {tr('of_bill', lang)}")
k[2].metric(tr("kpi_forecast", lang), money(s.forecast_month_end))
k[3].metric(tr("kpi_runrate", lang), money(s.run_rate_monthly))
k[4].metric(tr("kpi_anomalies", lang), len(s.anomalies))
k[5].metric(tr("kpi_untagged", lang), f"{s.untagged_pct:.0f}%" if s.untagged_pct is not None else "—")
if s.period_start is not None:
    st.caption(f"{tr('kpi_period', lang)}: {s.period_start:%Y-%m-%d} → {s.period_end:%Y-%m-%d} "
               f"({s.days}d) · {s.line_items:,} {tr('line_items', lang)} · {s.services} services")
st.caption(tr("disclaimer", lang))

tabs = st.tabs([tr(x, lang) for x in
                ("t_overview", "t_savings", "t_anomalies", "t_explorer", "t_ai", "t_chat", "t_export")])
other = tr("other", lang)

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
with tabs[0]:
    labels = {"daily": tr("l_daily", lang), "avg7": tr("l_avg7", lang), "anomaly": tr("l_anomaly", lang)}
    fig = charts.daily_trend(s, tr("c_daily", lang), labels)
    if fig:
        if budget > 0 and s.forecast_month_end:
            c1, c2 = st.columns([3, 1])
            c1.plotly_chart(fig, width="stretch")
            c2.plotly_chart(charts.budget_gauge(s.forecast_month_end, budget, tr("c_budget", lang)),
                            width="stretch")
            if s.forecast_month_end > budget:
                c2.error(tr("budget_over", lang, amount=money(s.forecast_month_end - budget)))
            else:
                c2.success(tr("budget_ok", lang, pct=s.forecast_month_end / budget * 100))
        else:
            st.plotly_chart(fig, width="stretch")
    else:
        st.info(tr("no_dates", lang))

    c1, c2 = st.columns(2)
    c1.plotly_chart(charts.service_donut(s, tr("c_donut", lang), other), width="stretch")
    c2.plotly_chart(charts.top_services_bar(s, tr("c_top", lang)), width="stretch")

    fig = charts.service_trend(bill.df, tr("c_stack", lang), other=other)
    if fig:
        st.plotly_chart(fig, width="stretch")
    c1, c2 = st.columns(2)
    fig = charts.region_bar(s, tr("c_region", lang))
    if fig:
        c1.plotly_chart(fig, width="stretch")
    fig = charts.treemap(bill.df, tr("c_tree", lang))
    if fig:
        (c2 if charts.region_bar(s, "") else st).plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Savings plan
# ---------------------------------------------------------------------------
with tabs[1]:
    if not a.findings:
        st.success(tr("sav_none", lang))
    else:
        st.subheader(tr("sav_header", lang, n=len(a.findings), amount=money(a.total_savings), pct=sav_pct))
        st.caption(tr("sav_note", lang))
        fig = charts.savings_waterfall(s.total, a, tr("c_waterfall", lang),
                                       {"current": tr("l_current", lang), "optimized": tr("l_optimized", lang)},
                                       lang)
        if fig:
            st.plotly_chart(fig, width="stretch")

        visible = a.findings if is_pro else a.findings[:cfg.free_findings]
        locked = [] if is_pro else a.findings[cfg.free_findings:]
        for f in visible:
            head = f"{SEV_ICON[f.severity]} **{f.title}** — {tr('est_savings', lang)}: **{money(f.savings)}**"
            with st.expander(head, expanded=f.severity == "high"):
                m = st.columns(4)
                m[0].metric(tr("severity", lang), tr(f"sev_{f.severity}", lang))
                m[1].metric(tr("confidence", lang), tr(f"sev_{f.confidence}", lang))
                m[2].metric(tr("affected", lang), money(f.affected_cost))
                m[3].metric(tr("line_items", lang), f.rows)
                st.markdown(f"**{tr('action', lang)}:** {f.action}")
                if f.examples:
                    st.markdown(f"**{tr('top_resources', lang)}:**")
                    st.markdown("\n".join(f"- `{e}`" for e in f.examples))

        if locked:
            st.warning(tr("locked_findings", lang, n=len(locked), amount=money(sum(f.savings for f in locked))))
            upgrade_cta(lang)

    if a.findings and is_pro:
        st.subheader(tr("top_lines", lang))
        rule_title = {r.id: r.title[lang] for r in rules.RULES}
        lines = (bill.df.drop(columns=["text", "tagged"])
                 .assign(savings=a.row_savings, rule=a.row_rule.map(rule_title).fillna(""))
                 .query("savings > 0").sort_values("savings", ascending=False).head(200))
        st.dataframe(lines, width="stretch", hide_index=True, column_config={
            "cost": st.column_config.NumberColumn(format="$%.2f"),
            "savings": st.column_config.ProgressColumn(format="$%.2f", min_value=0,
                                                       max_value=float(lines["savings"].max() or 1)),
            "date": st.column_config.DateColumn(),
        })

# ---------------------------------------------------------------------------
# Anomalies & governance
# ---------------------------------------------------------------------------
with tabs[2]:
    if not a.insights and not s.anomalies:
        st.success(tr("an_none", lang))
    for i in a.insights:
        box = st.error if i.severity == "high" else st.warning
        box(f"{SEV_ICON[i.severity]} **{i.title}**\n\n{i.action}")
    if s.anomalies:
        st.subheader(tr("an_table", lang))
        st.dataframe(pd.DataFrame([{
            "type": tr(f"an_kind_{x.kind}", lang), "when / what": x.label, "service": x.service,
            "cost": x.cost, "expected": x.expected, "excess": x.excess, "score": round(x.score, 1),
        } for x in s.anomalies]), width="stretch", hide_index=True, column_config={
            "cost": st.column_config.NumberColumn(format="$%.2f"),
            "expected": st.column_config.NumberColumn(format="$%.2f"),
            "excess": st.column_config.NumberColumn(format="$%.2f"),
        })
    if bill.warnings:
        with st.expander(tr("warnings", lang)):
            for w in bill.warnings:
                st.write("• " + w)

# ---------------------------------------------------------------------------
# Explorer
# ---------------------------------------------------------------------------
with tabs[3]:
    df = bill.df.assign(savings=a.row_savings)
    c1, c2, c3 = st.columns(3)
    svc = c1.multiselect(tr("ex_service", lang), sorted(df["service"].unique()))
    reg = c2.multiselect(tr("ex_region", lang), sorted(df["region"].unique()))
    accts = sorted(x for x in df["account"].unique() if x)
    acc = c3.multiselect(tr("ex_account", lang), accts) if accts else []
    c1, c2, c3 = st.columns([2, 2, 1])
    q = c1.text_input(tr("ex_search", lang))
    rng = None
    if bill.has_dates:
        dmin, dmax = df["date"].min().date(), df["date"].max().date()
        rng = c2.date_input(tr("ex_dates", lang), (dmin, dmax), min_value=dmin, max_value=dmax)
    group = c3.selectbox(tr("ex_group", lang), ["service", "region", "account", "resource", "usage"])

    f = df
    if svc:
        f = f[f["service"].isin(svc)]
    if reg:
        f = f[f["region"].isin(reg)]
    if acc:
        f = f[f["account"].isin(acc)]
    if q:
        f = f[f["text"].str.contains(q.lower(), regex=False, na=False)
              | f["service"].str.lower().str.contains(q.lower(), regex=False)]
    if rng and isinstance(rng, (list, tuple)) and len(rng) == 2:
        f = f[(f["date"] >= pd.Timestamp(rng[0])) & (f["date"] <= pd.Timestamp(rng[1]))]

    st.caption(tr("ex_rows", lang, n=f"{len(f):,}", amount=money(f["cost"].sum(), 2)))
    pivot = (f.groupby(group)[["cost", "savings"]].sum().sort_values("cost", ascending=False)
             .reset_index().head(100))
    st.dataframe(pivot, width="stretch", hide_index=True, column_config={
        "cost": st.column_config.NumberColumn(format="$%.2f"),
        "savings": st.column_config.NumberColumn(format="$%.2f")})
    view = f.drop(columns=["text"]).sort_values("cost", ascending=False)
    st.dataframe(view.head(5000), width="stretch", hide_index=True, column_config={
        "cost": st.column_config.NumberColumn(format="$%.4f"),
        "savings": st.column_config.NumberColumn(format="$%.4f"),
        "date": st.column_config.DateColumn()})
    st.download_button(tr("ex_dl", lang), view.to_csv(index=False).encode("utf-8-sig"),
                       "filtered_line_items.csv", "text/csv")

# ---------------------------------------------------------------------------
# AI report & chat
# ---------------------------------------------------------------------------
context = ai.build_context(bill, s, a)
ai_limit = cfg.ai_requests_per_session


def ai_blocked() -> str | None:
    """Return a message if AI can't be used right now, else None."""
    if not api_key:
        return tr("ai_need_key", lang) if is_pro else tr("ai_own_key", lang)
    if using_owner_key and ss.ai_used >= ai_limit:
        return tr("ai_limit", lang, n=ai_limit)
    return None


def ai_quota_note(where=st):
    if using_owner_key:
        where.caption(tr("ai_remaining", lang, n=max(ai_limit - ss.ai_used, 0)))


with tabs[4]:
    st.caption(tr("ai_intro", lang))
    existing = ss.ai_text.get(analysis_key)
    blocked = ai_blocked()
    if blocked:
        st.warning(blocked)
    elif st.button(tr("ai_regen" if existing else "ai_btn", lang), type="primary"):
        ss.ai_used += 1 if using_owner_key else 0
        try:
            text = st.write_stream(ai.stream_report(api_key, context, lang, model))
            existing = text if isinstance(text, str) else "".join(map(str, text))
            ss.ai_text[analysis_key] = existing
            existing = None  # already shown by write_stream
        except Exception as e:  # noqa: BLE001
            st.error(ai_error_message(e, lang))
    if existing:
        st.markdown(existing)
    ai_quota_note()

with tabs[5]:
    history = ss.chat.setdefault(analysis_key, [])
    chat_box = st.container(height=480)
    for m in history:
        chat_box.chat_message(m["role"]).markdown(m["content"])
    blocked = ai_blocked()
    if blocked:
        st.warning(blocked)
    else:
        suggestion = st.pills("💡", tr("chat_suggestions", lang), key=f"pill_{len(history)}",
                              label_visibility="collapsed")
        typed = st.chat_input(tr("chat_placeholder", lang))
        question = typed or suggestion
        if question:
            ss.ai_used += 1 if using_owner_key else 0
            history.append({"role": "user", "content": question})
            chat_box.chat_message("user").markdown(question)
            with chat_box.chat_message("assistant"):
                try:
                    answer = st.write_stream(ai.stream_chat(api_key, context, history[:-1], question, lang, model))
                    history.append({"role": "assistant",
                                    "content": answer if isinstance(answer, str) else "".join(map(str, answer))})
                except Exception as e:  # noqa: BLE001
                    history.pop()
                    st.error(ai_error_message(e, lang))
        ai_quota_note()
    if history and st.button(tr("chat_clear", lang)):
        ss.chat[analysis_key] = []
        st.rerun()

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
with tabs[6]:
    if not is_pro:
        st.warning(tr("locked_exports", lang))
        st.info(tr("pro_perks", lang))
        upgrade_cta(lang)
    else:
        st.caption(tr("exp_intro", lang))
        ai_text = ss.ai_text.get(analysis_key)
        exp = session_cached("_exports", f"{analysis_key}|{hash(ai_text)}", lambda: {
            "pdf": report.to_pdf(bill, s, a, lang, ai_text),
            "xlsx": report.to_excel(bill, s, a, lang, ai_text),
            "md": report.to_markdown(bill, s, a, lang, ai_text),
        })
        c = st.columns(4)
        c[0].download_button(tr("exp_pdf", lang), exp["pdf"], "cloud_bill_audit.pdf", "application/pdf",
                             width="stretch", type="primary")
        c[1].download_button(tr("exp_xlsx", lang), exp["xlsx"], "cloud_bill_audit.xlsx",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             width="stretch")
        c[2].download_button(tr("exp_md", lang), exp["md"].encode("utf-8"), "cloud_bill_audit.md",
                             "text/markdown", width="stretch")
        lines_csv = (bill.df.drop(columns=["text"]).assign(estimated_savings=a.row_savings, rule=a.row_rule)
                     .to_csv(index=False).encode("utf-8-sig"))
        c[3].download_button(tr("exp_csv", lang), lines_csv, "line_items_with_savings.csv", "text/csv",
                             width="stretch")
        with st.expander("Markdown preview"):
            st.markdown(exp["md"])

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.subheader(tr("b2b_header", lang))
st.write(tr("b2b_text", lang))
st.info(f"{tr('b2b_contact', lang)} {cfg.contact_email}")
st.caption(f"[{tr('terms', lang)}]({REPO_URL}/TERMS.md) · [{tr('privacy_link', lang)}]({REPO_URL}/PRIVACY.md) · "
           f"© Cloud Bill Auditor v{__version__}")
