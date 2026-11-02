"""FinOps rules engine.

Each rule pattern-matches the normalized line items and estimates how much
of each matching row's cost can realistically be saved. When several rules
match the same row, the *total* potential savings only counts the single
best rule for that row, so savings are never double-counted.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from .analytics import Summary
from .parsing import Bill

HIGH, MEDIUM, LOW, INFO = "high", "medium", "low", "info"
SEVERITY_ORDER = {HIGH: 0, MEDIUM: 1, LOW: 2, INFO: 3}

COMPUTE_RE = re.compile(
    r"ec2|compute|virtual machine|\bvm\b|instance|boxusage|rds|cloud ?sql|sql database|"
    r"database|aurora|kubernetes|\beks\b|\bgke\b|\baks\b|fargate|container|app service|elasticache|"
    r"\bbatch\b|\bemr\b|dataproc|databricks|vcpu|\bnodes?\b"
)


@dataclass
class Rule:
    id: str
    category: str
    severity: str
    confidence: str
    pattern: re.Pattern
    savings: float | Callable[[str], float]
    title: dict
    action: dict
    scope: re.Pattern | None = None      # row must ALSO match this
    exclude: re.Pattern | None = None    # row must NOT match this

    def pct_for(self, text: str) -> float:
        if callable(self.savings):
            return max(0.0, min(1.0, self.savings(text)))
        return self.savings


@dataclass
class Finding:
    rule_id: str
    category: str
    severity: str
    confidence: str
    title: str
    action: str
    rows: int
    affected_cost: float
    savings: float
    examples: list[str] = field(default_factory=list)


@dataclass
class AuditResult:
    findings: list[Finding]
    insights: list[Finding]         # governance items without a $ estimate
    row_savings: pd.Series          # best savings per line item (deduplicated)
    row_rule: pd.Series             # which rule produced it

    @property
    def total_savings(self) -> float:
        return float(self.row_savings.sum())

    def savings_by_category(self) -> pd.DataFrame:
        if not self.findings:
            return pd.DataFrame(columns=["category", "savings"])
        cat = {f.rule_id: f.category for f in self.findings}
        s = self.row_savings[self.row_savings > 0]
        df = pd.DataFrame({"category": self.row_rule[s.index].map(cat), "savings": s})
        return (df.groupby("category")["savings"].sum().reset_index()
                .sort_values("savings", ascending=False))


# ---------------------------------------------------------------------------
# Dynamic savings helpers
# ---------------------------------------------------------------------------
_UNUSED_PCT = re.compile(r"(?:unused|idle|wasted?)\D{0,3}(\d{1,3})\s*%|(\d{1,3})\s*%\s*(?:unused|idle)")
_UTIL_PCT = re.compile(r"(?:utili[sz]ation|util|cpu)\D{0,4}(\d{1,3}(?:\.\d+)?)\s*%")


def _underutilized_savings(text: str) -> float:
    m = _UNUSED_PCT.search(text)
    if m:
        unused = float(m.group(1) or m.group(2)) / 100
        return unused * 0.85       # can't usually reclaim 100% of headroom
    m = _UTIL_PCT.search(text)
    if m:
        util = float(m.group(1)) / 100
        if util < 0.4:
            # Rightsizing one or two sizes down roughly halves cost per step.
            return 0.5 if util < 0.2 else 0.3
    return 0.0


def _t(en: str, ar: str) -> dict:
    return {"English": en, "العربية": ar}


RULES: list[Rule] = [
    Rule(
        "idle", "Idle & orphaned resources", HIGH, "high",
        re.compile(r"\b(unused|idle|unattached|orphan(?:ed)?|stopped|detached|not[ -]attached|zombie|"
                   r"available volume|unassociated)\b(?!\D{0,3}\d{1,3}\s*%)"),
        1.0,
        _t("Idle, stopped or unattached resources",
           "موارد خاملة أو متوقفة أو غير مرتبطة"),
        _t("Delete or release them (snapshot first if needed). Unattached volumes, idle load "
           "balancers and stopped instances with attached storage keep billing every hour.",
           "احذفها أو حررها (خذ نسخة احتياطية أولاً عند الحاجة). الأقراص غير المرتبطة وموازنات الحمل "
           "الخاملة والخوادم المتوقفة ذات التخزين المرتبط تستمر بالفوترة كل ساعة."),
    ),
    Rule(
        "underutilized", "Rightsizing", HIGH, "high",
        re.compile(_UNUSED_PCT.pattern + "|" + _UTIL_PCT.pattern),
        _underutilized_savings,
        _t("Under-utilized (over-provisioned) resources",
           "موارد مستغلة جزئياً (حجم أكبر من الحاجة)"),
        _t("Downsize to the next smaller instance/machine type or enable autoscaling. "
           "Check 14–30 days of CPU and memory metrics before changing.",
           "قلّص الحجم إلى نوع أصغر أو فعّل التوسع التلقائي. راجع مقاييس المعالج والذاكرة "
           "لمدة 14-30 يوماً قبل التغيير."),
    ),
    Rule(
        "dev_247", "Scheduling", MEDIUM, "medium",
        re.compile(r"(?<!/)\b(dev|development|test|testing|qa|staging|stage|sandbox|demo|poc|uat)\b"),
        0.6,
        _t("Non-production workloads running 24/7",
           "بيئات غير إنتاجية (تطوير/اختبار) تعمل على مدار الساعة"),
        _t("Schedule dev/test/staging to stop outside working hours (e.g. 12h × 5 days "
           "≈ 65% fewer hours) using Instance Scheduler, Cloud Scheduler or Azure Automation.",
           "جدول إيقاف بيئات التطوير والاختبار خارج ساعات العمل (مثلاً 12 ساعة × 5 أيام توفر "
           "حوالي 65% من الساعات) عبر Instance Scheduler أو Cloud Scheduler أو Azure Automation."),
        scope=COMPUTE_RE,
    ),
    Rule(
        "public_ip", "Networking", MEDIUM, "medium",
        re.compile(r"elastic ?ip|idleaddress|public ?ipv4|public ?ip\b|static ?ip|external ?ip"),
        0.5,
        _t("Public IP address charges", "تكاليف عناوين IP العامة"),
        _t("Release unused Elastic/static IPs and move internal traffic to private addressing "
           "(public IPv4 is billed hourly on all major clouds).",
           "حرر عناوين IP الثابتة غير المستخدمة وانقل الحركة الداخلية إلى عناوين خاصة "
           "(عناوين IPv4 العامة تُفوتر بالساعة لدى جميع المزودين)."),
    ),
    Rule(
        "prev_gen", "Modernization", MEDIUM, "high",
        re.compile(r"\b(?:t1|t2|m1|m2|m3|m4|c1|c3|c4|r3|r4|i2|d2|g2|g3|p2|x1)\.(?:nano|micro|small|medium|"
                   r"large|\d*xlarge)\b|\bn1-(?:standard|highmem|highcpu)|\bstandard_[a-z]+\d+[a-z]*_v[12]\b"),
        0.15,
        _t("Previous-generation instance types", "أنواع خوادم من أجيال قديمة"),
        _t("Migrate to current generation (e.g. t2→t3/t4g, m4→m7g, n1→n2d/e2, Dv2→Dv5). "
           "Newer families are ~10–40% cheaper per unit of performance; ARM/Graviton even more.",
           "انتقل إلى الأجيال الحديثة (مثل t2←t3/t4g و m4←m7g و n1←n2d/e2 و Dv2←Dv5). "
           "الأجيال الأحدث أرخص بنحو 10-40% لنفس الأداء، ومعالجات ARM/Graviton أكثر توفيراً."),
    ),
    Rule(
        "gpu", "Rightsizing", MEDIUM, "low",
        re.compile(r"\b(?:p2|p3|p4d?|p5|g4dn|g5|g6|a2-highgpu|a3-|nc\d+|nd\d+|nv\d+)[\w.-]*|nvidia|\bgpu\b"),
        0.25,
        _t("Expensive GPU capacity", "سعة GPU مرتفعة التكلفة"),
        _t("Verify GPU utilization; use spot/preemptible GPUs for training, smaller GPUs or "
           "shared/fractional GPUs for inference, and shut down idle notebooks.",
           "تحقق من نسبة استغلال الـ GPU؛ استخدم خوادم Spot للتدريب وأنواعاً أصغر للاستدلال، "
           "وأوقف دفاتر Notebooks الخاملة."),
    ),
    Rule(
        "spot", "Purchasing", MEDIUM, "medium",
        re.compile(r"\b(emr|dataproc|batch|databricks|spark|hadoop|ci[- ]?runner|jenkins|build|"
                   r"worker|render|etl)\b"),
        0.5,
        _t("Fault-tolerant workloads on on-demand capacity",
           "أحمال عمل قابلة للمقاطعة تعمل بأسعار On-Demand"),
        _t("Run batch, CI, big-data and worker fleets on Spot / Preemptible / Azure Spot VMs "
           "(typically 60–90% cheaper).",
           "شغّل أحمال المعالجة الدفعية و CI والبيانات الضخمة على خوادم Spot / Preemptible "
           "(أرخص عادة بنسبة 60-90%)."),
        scope=COMPUTE_RE,
        exclude=re.compile(r"\bspot\b|preemptible"),
    ),
    Rule(
        "snapshots", "Storage", MEDIUM, "medium",
        re.compile(r"snapshot|backup|\bami\b|machine image|recovery ?point|vault"),
        0.3,
        _t("Snapshot & backup retention", "الاحتفاظ بالنسخ الاحتياطية واللقطات"),
        _t("Apply retention policies (e.g. keep 7 daily, 4 weekly, 12 monthly), delete snapshots "
           "of deleted volumes and move long-term backups to archive tiers.",
           "طبّق سياسات احتفاظ (مثلاً 7 يومية و4 أسبوعية و12 شهرية)، واحذف لقطات الأقراص المحذوفة "
           "وانقل النسخ طويلة الأمد إلى طبقات الأرشفة."),
    ),
    Rule(
        "logs", "Observability", MEDIUM, "medium",
        re.compile(r"cloudwatch|putlogevents|log ?ingest|logging|log analytics|log-group|loggroup|"
                   r"verbose|error_loop|datadog|stackdriver|stdout"),
        0.35,
        _t("High log ingestion / observability cost", "تكاليف مرتفعة لإدخال السجلات (Logs)"),
        _t("Lower log levels in production, drop debug/health-check logs, set retention "
           "(e.g. 30 days) and export cold logs to object storage.",
           "خفّض مستوى السجلات في الإنتاج، واستبعد سجلات التصحيح وفحوص الصحة، وحدد مدة احتفاظ "
           "(مثلاً 30 يوماً) وصدّر السجلات القديمة إلى التخزين الكائني."),
    ),
    Rule(
        "network", "Networking", MEDIUM, "medium",
        re.compile(r"nat ?gateway|natgateway|data ?transfer|datatransfer|egress|internet ?out|"
                   r"bandwidth|inter-?region|inter-?zone|\baz\b transfer"),
        0.25,
        _t("Data transfer & NAT gateway charges", "تكاليف نقل البيانات وبوابات NAT"),
        _t("Add VPC/S3/GCS endpoints to bypass NAT, keep chatty services in the same zone, "
           "cache with a CDN and compress responses.",
           "أضف VPC Endpoints لتجاوز NAT، وأبقِ الخدمات المتواصلة كثيراً في نفس المنطقة، "
           "واستخدم CDN للتخزين المؤقت مع ضغط الاستجابات."),
    ),
    Rule(
        "storage_tier", "Storage", LOW, "medium",
        re.compile(r"standard storage|timedstorage|s3 standard|\bs3\b|cloud storage|blob storage|"
                   r"hot tier|object storage|\bgcs\b|\bgp2\b|io1"),
        0.2,
        _t("Object/block storage on expensive tiers", "تخزين على طبقات مرتفعة السعر"),
        _t("Enable lifecycle rules / Intelligent-Tiering to move cold data to IA/Nearline/Cool "
           "tiers, and migrate gp2/io1 volumes to gp3.",
           "فعّل قواعد دورة الحياة أو Intelligent-Tiering لنقل البيانات الباردة إلى طبقات أرخص، "
           "وانقل أقراص gp2/io1 إلى gp3."),
        exclude=re.compile(r"snapshot|backup|archive|glacier|coldline|nearline"),
    ),
    Rule(
        "oversized", "Rightsizing", LOW, "low",
        re.compile(r"\b\d{2,}xlarge\b|-(?:standard|highmem|highcpu)-(?:32|48|64|80|96)\b|_[de](?:32|48|64|96)"),
        0.2,
        _t("Very large instance sizes", "خوادم بأحجام كبيرة جداً"),
        _t("Validate that these large sizes are needed; horizontal scaling with smaller nodes "
           "is often cheaper and more resilient.",
           "تحقق من الحاجة الفعلية لهذه الأحجام الكبيرة؛ التوسع الأفقي بعقد أصغر أرخص وأكثر مرونة غالباً."),
    ),
    Rule(
        "commitment", "Purchasing", MEDIUM, "medium",
        COMPUTE_RE,
        0.28,
        _t("Steady compute/database usage without commitment discounts",
           "استخدام ثابت للحوسبة وقواعد البيانات بدون خصومات الالتزام"),
        _t("Cover your stable baseline with Savings Plans / Reserved Instances / Committed Use "
           "Discounts (1-year no-upfront ≈ 25–40% off). Start with ~70% of the minimum hourly usage.",
           "غطِّ الاستخدام الأساسي الثابت بـ Savings Plans أو Reserved Instances أو Committed Use "
           "Discounts (التزام سنة بدون دفع مقدم يوفر 25-40%). ابدأ بتغطية 70% من الحد الأدنى للاستخدام."),
        exclude=re.compile(r"reserved|savings ?plan|commit|\bcud\b|\bri\b|spot|preemptible|"
                           r"snapshot|backup|data ?transfer|storage|\btax\b|credit|support"),
    ),
]

RULES_BY_ID = {r.id: r for r in RULES}

CATEGORY_AR = {
    "Idle & orphaned resources": "موارد خاملة ومتروكة", "Rightsizing": "تعديل الأحجام",
    "Scheduling": "جدولة التشغيل", "Networking": "الشبكات", "Modernization": "التحديث",
    "Purchasing": "خطط الشراء", "Storage": "التخزين", "Observability": "السجلات والمراقبة",
    "Governance": "الحوكمة", "Trend": "الاتجاه", "Anomaly": "انحراف",
}


def category_label(category: str, lang: str) -> str:
    return CATEGORY_AR.get(category, category) if lang == "العربية" else category


def _contains(texts: pd.Series, pattern: re.Pattern) -> pd.Series:
    with warnings.catch_warnings():   # "pattern has match groups" is harmless here
        warnings.simplefilter("ignore", UserWarning)
        return texts.str.contains(pattern, na=False).astype(bool)


def _row_matches(rule: Rule, texts: pd.Series) -> pd.Series:
    mask = _contains(texts, rule.pattern)
    if rule.scope is not None:
        mask &= _contains(texts, rule.scope)
    if rule.exclude is not None:
        mask &= ~_contains(texts, rule.exclude)
    return mask


def run_rules(bill: Bill, summary: Summary, lang: str = "English",
              disabled: set[str] | None = None, min_commit_spend: float = 50.0) -> AuditResult:
    df = bill.df
    disabled = disabled or set()
    # Include service/usage so rules match even if those columns weren't text in the raw file.
    texts = (df["text"] + " " + df["service"].str.lower() + " " + df["usage"].str.lower()).str.lower()
    positive = df["cost"] > 0

    per_rule: dict[str, pd.Series] = {}
    findings: list[Finding] = []

    for rule in RULES:
        if rule.id in disabled:
            continue
        mask = _row_matches(rule, texts) & positive
        if not mask.any():
            continue
        pct = texts[mask].map(rule.pct_for)
        savings = (df.loc[mask, "cost"] * pct).round(4)
        if rule.id == "commitment" and df.loc[mask, "cost"].sum() < min_commit_spend:
            continue
        if savings.sum() <= 0:
            continue
        per_rule[rule.id] = savings.reindex(df.index, fill_value=0.0)

        sub = df.loc[mask]
        # Aggregate per resource so a resource billed daily shows up once.
        label = sub["resource"].where(sub["resource"] != "", sub["usage"]).str.slice(0, 60)
        top = (pd.DataFrame({"service": sub["service"], "label": label, "amount": savings})
               .groupby(["service", "label"])["amount"].sum().nlargest(5).reset_index())
        examples = [f"{r.service} · {r.label} (${r.amount:,.0f})" if r.label else str(r.service)
                    for r in top.itertuples()]
        findings.append(Finding(
            rule_id=rule.id, category=rule.category, severity=rule.severity,
            confidence=rule.confidence, title=rule.title[lang], action=rule.action[lang],
            rows=int(mask.sum()), affected_cost=float(sub["cost"].sum()),
            savings=float(savings.sum()), examples=examples,
        ))

    if per_rule:
        matrix = pd.DataFrame(per_rule)
        row_savings = matrix.max(axis=1).clip(upper=df["cost"].clip(lower=0))
        row_rule = matrix.idxmax(axis=1).where(row_savings > 0, "")
    else:
        row_savings = pd.Series(0.0, index=df.index)
        row_rule = pd.Series("", index=df.index)

    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], -f.savings))
    return AuditResult(findings=findings, insights=_insights(bill, summary, lang),
                       row_savings=row_savings, row_rule=row_rule)


def _insights(bill: Bill, s: Summary, lang: str) -> list[Finding]:
    ar = lang == "العربية"
    out: list[Finding] = []

    if s.total > 0 and not s.by_service.empty:
        top = s.by_service.iloc[0]
        if top["share_pct"] >= 40:
            out.append(Finding(
                "concentration", "Governance", MEDIUM, "high",
                (f"تركّز التكلفة: خدمة ({top['service']}) تمثل {top['share_pct']:.0f}% من الفاتورة"
                 if ar else f"Cost concentration: {top['service']} is {top['share_pct']:.0f}% of the bill"),
                ("ابدأ التحسين بهذه الخدمة أولاً فهي ذات أعلى عائد، وفعّل تنبيهات ميزانية خاصة بها."
                 if ar else "Focus optimization here first — it has the highest ROI — and set a "
                            "dedicated budget alert for it."),
                int(top["line_items"]), float(top["cost"]), 0.0))

    if s.untagged_pct is not None and s.untagged_pct >= 20:
        out.append(Finding(
            "untagged", "Governance", MEDIUM if s.untagged_pct < 50 else HIGH, "high",
            (f"{s.untagged_pct:.0f}% من التكلفة بدون وسوم (Tags)" if ar
             else f"{s.untagged_pct:.0f}% of spend is untagged"),
            ("فرض سياسة وسوم إلزامية (owner, env, cost-center) عبر Tag Policies أو Azure Policy "
             "لتوزيع التكاليف على الفرق." if ar else
             "Enforce mandatory tags (owner, env, cost-center) via Tag Policies / Azure Policy / "
             "Org Policy so every dollar has an owner (showback/chargeback)."),
            0, float(s.untagged_cost or 0), 0.0))

    if s.mom_change_pct is not None and s.mom_change_pct >= 15:
        out.append(Finding(
            "growth", "Trend", HIGH if s.mom_change_pct >= 40 else MEDIUM, "medium",
            (f"ارتفاع الإنفاق بنسبة {s.mom_change_pct:.0f}% مقارنة بالشهر السابق" if ar
             else f"Spend is up {s.mom_change_pct:.0f}% vs. the previous month (same days)"),
            ("حدد الخدمات المسببة للزيادة في الرسم البياني اليومي وتأكد أنها متوقعة." if ar
             else "Use the daily trend to find which services drove the increase and confirm it was planned."),
            0, 0.0, 0.0))

    for a in s.anomalies[:5]:
        when = a.label if a.kind == "daily" else a.label
        out.append(Finding(
            "anomaly", "Anomaly", HIGH, "medium",
            (f"قفزة شاذة: {a.service} ({when}) — ${a.cost:,.2f} مقابل ${a.expected:,.2f} متوقع" if ar
             else f"Anomaly: {a.service} ({when}) — ${a.cost:,.2f} vs ${a.expected:,.2f} expected"),
            ("راجع ما تغيّر في هذا التاريخ (نشر جديد، حلقة أخطاء، زيادة حركة) وفعّل AWS Cost Anomaly "
             "Detection أو ما يعادله." if ar else
             "Check what changed at that time (deploy, error loop, traffic surge) and enable native "
             "anomaly alerts (AWS Cost Anomaly Detection / GCP budgets / Azure anomaly alerts)."),
            1, a.cost, 0.0))
    return out
