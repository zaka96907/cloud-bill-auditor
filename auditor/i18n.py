"""UI strings (English / Arabic)."""

EN, AR = "English", "العربية"
LANGUAGES = [EN, AR]

_T = {
    # --- general -----------------------------------------------------------
    "app_title": ("Smart Cloud Bill Auditor", "مفتش الفواتير السحابية الذكي"),
    "app_subtitle": ("Find waste, quantify savings and get an actionable FinOps plan for AWS, GCP & Azure.",
                     "اكتشف الهدر المالي، واحسب التوفير بدقة، واحصل على خطة FinOps تنفيذية لـ AWS و GCP و Azure."),
    "lang_label": ("Language", "اللغة"),
    # --- sidebar -------------------------------------------------------------
    "sb_ai": ("AI settings (optional)", "إعدادات الذكاء الاصطناعي (اختياري)"),
    "api_label": ("Gemini API key", "مفتاح Gemini API"),
    "api_help": ("Only needed for the AI report and chat. The audit, charts and exports work without it.",
                 "مطلوب فقط لتقرير الذكاء الاصطناعي والمحادثة. التدقيق والرسوم والتصدير تعمل بدونه."),
    "api_link": ("Get a free key", "احصل على مفتاح مجاني"),
    "model_label": ("Model", "النموذج"),
    "sb_settings": ("Audit settings", "إعدادات التدقيق"),
    "budget_label": ("Monthly budget (USD, 0 = none)", "الميزانية الشهرية (دولار، 0 = بدون)"),
    "sensitivity_label": ("Anomaly sensitivity", "حساسية كشف الانحرافات"),
    "sensitivity_help": ("Lower = more anomalies flagged.", "قيمة أقل = عدد أكبر من الانحرافات."),
    "rules_label": ("Active rules", "القواعد المفعّلة"),
    "privacy": ("🔒 Your bill is processed in memory for your browser session only — it is never written "
                "to disk or shared with other users, and it is discarded when you press Clear or close the tab. "
                "Only an aggregated summary (not the raw file) is sent to Google Gemini, and only when you "
                "request AI analysis.",
                "🔒 تتم معالجة الفاتورة في الذاكرة لجلستك فقط — لا تُحفظ على القرص ولا تُشارك مع مستخدمين آخرين، "
                "وتُحذف عند الضغط على مسح أو إغلاق الصفحة. يُرسل ملخص مجمّع فقط (وليس الملف الخام) إلى "
                "Google Gemini، وفقط عند طلب التحليل بالذكاء الاصطناعي."),
    # --- input -------------------------------------------------------------
    "tab_upload": ("📤 Upload bill", "📤 رفع الفاتورة"),
    "tab_sample": ("🧪 Try a sample", "🧪 جرّب فاتورة تجريبية"),
    "uploader_label": ("Upload one or more billing exports (CSV, CSV.GZ, ZIP, XLSX, JSON, Parquet)",
                       "ارفع ملف فوترة أو أكثر (CSV أو CSV.GZ أو ZIP أو XLSX أو JSON أو Parquet)"),
    "uploader_help": ("AWS CUR / Cost Explorer, GCP billing export, Azure cost details, or any CSV with a cost column. "
                      "Upload several months at once to get month-over-month trends.",
                      "يدعم AWS CUR و Cost Explorer وتصدير فوترة GCP وتفاصيل تكاليف Azure أو أي ملف يحتوي عمود تكلفة. "
                      "ارفع عدة أشهر معاً للحصول على مقارنة شهرية."),
    "sample_provider": ("Sample provider", "مزود الفاتورة التجريبية"),
    "sample_btn": ("Generate a 30-day sample bill", "توليد فاتورة تجريبية لمدة 30 يوماً"),
    "sample_ok": ("Sample bill loaded — it contains planted waste so you can see every feature.",
                  "تم تحميل الفاتورة التجريبية — تحتوي على هدر متعمد لعرض جميع المميزات."),
    "empty_state": ("Upload a bill or generate a sample to start the audit.",
                    "ارفع فاتورة أو ولّد فاتورة تجريبية لبدء التدقيق."),
    "clear": ("Clear", "مسح"),
    "mapping": ("🧭 Detected columns (click to adjust)", "🧭 الأعمدة المكتشفة (اضغط للتعديل)"),
    "mapping_help": ("Auto-detected. Change any field if the detection is wrong.",
                     "تم الكشف تلقائياً. غيّر أي حقل إذا كان الكشف غير صحيح."),
    "auto": ("(auto)", "(تلقائي)"),
    "error_read": ("Could not read this file", "تعذّرت قراءة هذا الملف"),
    "provider": ("Provider", "المزود"),
    # --- KPIs --------------------------------------------------------------
    "kpi_total": ("Total spend", "إجمالي الإنفاق"),
    "kpi_savings": ("Potential savings", "التوفير المحتمل"),
    "kpi_forecast": ("Month-end forecast", "توقع نهاية الشهر"),
    "kpi_runrate": ("Monthly run-rate", "معدل الإنفاق الشهري"),
    "kpi_anomalies": ("Anomalies", "الانحرافات"),
    "kpi_untagged": ("Untagged spend", "إنفاق بدون وسوم"),
    "kpi_period": ("Period", "الفترة"),
    "of_bill": ("of bill", "من الفاتورة"),
    "vs_prev": ("vs prev. month", "مقارنة بالشهر السابق"),
    # --- tabs ----------------------------------------------------------------
    "t_overview": ("📊 Overview", "📊 نظرة عامة"),
    "t_savings": ("💰 Savings plan", "💰 خطة التوفير"),
    "t_anomalies": ("🚨 Anomalies & governance", "🚨 الانحرافات والحوكمة"),
    "t_explorer": ("🔎 Explorer", "🔎 مستكشف البيانات"),
    "t_ai": ("🤖 AI report", "🤖 تقرير الذكاء الاصطناعي"),
    "t_chat": ("💬 Ask your bill", "💬 اسأل فاتورتك"),
    "t_export": ("📥 Export", "📥 التصدير"),
    # --- charts --------------------------------------------------------------
    "c_daily": ("Daily spend & anomalies", "الإنفاق اليومي والانحرافات"),
    "c_donut": ("Cost by service", "التكلفة حسب الخدمة"),
    "c_top": ("Top services", "أعلى الخدمات تكلفة"),
    "c_stack": ("Daily spend by service", "الإنفاق اليومي حسب الخدمة"),
    "c_region": ("Cost by region", "التكلفة حسب المنطقة"),
    "c_tree": ("Service → resource breakdown", "تفصيل الخدمات ← الموارد"),
    "c_budget": ("Forecast vs budget", "التوقع مقابل الميزانية"),
    "c_waterfall": ("From current spend to optimized spend", "من الإنفاق الحالي إلى الإنفاق المحسّن"),
    "l_daily": ("Daily cost", "التكلفة اليومية"),
    "l_avg7": ("7-day average", "متوسط 7 أيام"),
    "l_anomaly": ("Anomaly", "انحراف"),
    "l_current": ("Current", "الحالي"),
    "l_optimized": ("Optimized", "بعد التحسين"),
    "other": ("Other", "أخرى"),
    "no_dates": ("No date column found — upload a bill with daily line items to see trends and forecasts.",
                 "لم يتم العثور على عمود تاريخ — ارفع فاتورة ببنود يومية لعرض الاتجاهات والتوقعات."),
    "budget_over": ("⚠️ Forecast exceeds your budget by {amount}.", "⚠️ التوقع يتجاوز ميزانيتك بمقدار {amount}."),
    "budget_ok": ("✅ Forecast is within budget ({pct:.0f}% used).", "✅ التوقع ضمن الميزانية (مستخدم {pct:.0f}%)."),
    # --- savings tab -----------------------------------------------------------
    "sav_header": ("{n} opportunities · {amount} potential savings ({pct:.1f}% of the bill)",
                   "{n} فرصة توفير · {amount} توفير محتمل ({pct:.1f}% من الفاتورة)"),
    "sav_note": ("When several rules match the same line item, only the best one is counted, so the total is never double-counted.",
                 "عند تطابق عدة قواعد مع نفس البند، تُحتسب القاعدة الأفضل فقط، لذا لا يتكرر احتساب التوفير."),
    "sav_none": ("No savings opportunities detected by the rules engine.", "لم يكتشف محرك القواعد فرص توفير."),
    "severity": ("Severity", "الأولوية"),
    "confidence": ("Confidence", "الثقة"),
    "affected": ("Affected cost", "التكلفة المتأثرة"),
    "est_savings": ("Est. savings", "التوفير المتوقع"),
    "line_items": ("Line items", "البنود"),
    "action": ("Recommended action", "الإجراء الموصى به"),
    "top_resources": ("Top resources", "أهم الموارد"),
    "top_lines": ("Line items with the biggest savings", "البنود ذات أكبر توفير"),
    "sev_high": ("High", "عالية"), "sev_medium": ("Medium", "متوسطة"),
    "sev_low": ("Low", "منخفضة"), "sev_info": ("Info", "معلومة"),
    # --- anomalies tab ---------------------------------------------------------
    "an_none": ("No anomalies or governance issues detected. 🎉", "لم يتم اكتشاف انحرافات أو مشاكل حوكمة. 🎉"),
    "an_table": ("Detected anomalies", "الانحرافات المكتشفة"),
    "an_kind_daily": ("Daily spike", "قفزة يومية"),
    "an_kind_line_item": ("Outlier line item", "بند شاذ"),
    "warnings": ("Data quality notes", "ملاحظات جودة البيانات"),
    # --- explorer ------------------------------------------------------------
    "ex_service": ("Services", "الخدمات"),
    "ex_region": ("Regions", "المناطق"),
    "ex_account": ("Accounts / projects", "الحسابات / المشاريع"),
    "ex_dates": ("Date range", "نطاق التاريخ"),
    "ex_search": ("Search (resource, usage, any text)", "بحث (المورد، الاستخدام، أي نص)"),
    "ex_group": ("Group by", "تجميع حسب"),
    "ex_rows": ("{n} line items · {amount}", "{n} بند · {amount}"),
    "ex_dl": ("Download filtered CSV", "تحميل البيانات المفلترة CSV"),
    # --- AI --------------------------------------------------------------------
    "ai_intro": ("Gemini writes an executive report from the audit results (aggregated data only).",
                 "يكتب Gemini تقريراً تنفيذياً بناءً على نتائج التدقيق (بيانات مجمّعة فقط)."),
    "ai_btn": ("✨ Generate AI report", "✨ إنشاء تقرير الذكاء الاصطناعي"),
    "ai_regen": ("🔄 Regenerate", "🔄 إعادة الإنشاء"),
    "ai_need_key": ("Add your Gemini API key in the sidebar to enable AI features.",
                    "أضف مفتاح Gemini API في الشريط الجانبي لتفعيل مميزات الذكاء الاصطناعي."),
    "ai_busy": ("Gemini is busy (503/429). We retried automatically — please try again in a few seconds.",
                "خوادم Gemini مشغولة حالياً (503/429). أعدنا المحاولة تلقائياً — حاول مجدداً بعد ثوانٍ."),
    "ai_bad_key": ("The API key was rejected. Check it in Google AI Studio.",
                   "تم رفض مفتاح API. تحقق منه في Google AI Studio."),
    "ai_error": ("AI request failed", "فشل طلب الذكاء الاصطناعي"),
    "chat_placeholder": ("Ask anything about this bill…", "اسأل أي شيء عن هذه الفاتورة…"),
    "chat_suggestions": (["Which 3 actions save the most money this week?",
                          "Why is my bill high?",
                          "Should I buy Savings Plans or Reserved Instances?",
                          "Write a Slack message to the team about the top waste."],
                         ["ما هي أهم 3 إجراءات توفر أكبر مبلغ هذا الأسبوع؟",
                          "لماذا فاتورتي مرتفعة؟",
                          "هل أشتري Savings Plans أم Reserved Instances؟",
                          "اكتب رسالة للفريق عن أكبر مصادر الهدر."]),
    "chat_clear": ("Clear conversation", "مسح المحادثة"),
    # --- export ----------------------------------------------------------------
    "exp_intro": ("Download the full audit. The AI report is included if you generated one.",
                  "حمّل التدقيق الكامل. يتم تضمين تقرير الذكاء الاصطناعي إن كنت أنشأته."),
    "exp_pdf": ("📄 PDF report", "📄 تقرير PDF"),
    "exp_xlsx": ("📊 Excel workbook", "📊 ملف Excel"),
    "exp_md": ("📝 Markdown", "📝 Markdown"),
    "exp_csv": ("🧾 Line items + savings (CSV)", "🧾 البنود مع التوفير (CSV)"),
    # --- disclaimer / legal ----------------------------------------------------
    "disclaimer": ("ℹ️ Savings are estimates based on common FinOps benchmarks and the text of your bill, "
                   "not on your actual utilization metrics or negotiated prices. Validate each change before "
                   "acting. This is not financial advice.",
                   "ℹ️ أرقام التوفير تقديرية مبنية على معايير FinOps الشائعة ومحتوى الفاتورة، وليست على مقاييس "
                   "الاستخدام الفعلية أو أسعارك المتفاوض عليها. تحقق من كل تغيير قبل تنفيذه. هذه ليست استشارة مالية."),
    "terms": ("Terms", "الشروط"),
    "privacy_link": ("Privacy", "الخصوصية"),
    # --- plans -----------------------------------------------------------------
    "sb_plan": ("Plan", "الخطة"),
    "plan_free": ("Free plan", "الخطة المجانية"),
    "plan_pro": ("Pro plan ✅", "الخطة الاحترافية ✅"),
    "code_label": ("Access code", "رمز التفعيل"),
    "code_bad": ("Invalid access code.", "رمز التفعيل غير صحيح."),
    "code_ok": ("Pro unlocked. Thank you!", "تم تفعيل الخطة الاحترافية. شكراً لك!"),
    "buy_btn": ("⭐ Upgrade to Pro", "⭐ الترقية إلى الخطة الاحترافية"),
    "pro_perks": ("Pro unlocks: all savings findings, PDF/Excel/CSV exports, the AI report & chat without "
                  "your own key, and bills of any size.",
                  "الخطة الاحترافية تفتح: جميع فرص التوفير، تصدير PDF و Excel و CSV، تقرير ومحادثة الذكاء "
                  "الاصطناعي بدون مفتاحك الخاص، وفواتير بأي حجم."),
    "locked_findings": ("🔒 {n} more opportunities worth {amount} are available on the Pro plan.",
                        "🔒 {n} فرص توفير إضافية بقيمة {amount} متاحة في الخطة الاحترافية."),
    "locked_exports": ("🔒 Report exports are a Pro feature.", "🔒 تصدير التقارير متاح في الخطة الاحترافية."),
    "locked_size": ("🔒 The free plan analyzes bills up to {n:,} line items (this one has {m:,}). "
                    "Upgrade to Pro to analyze it.",
                    "🔒 الخطة المجانية تحلل فواتير حتى {n:,} بند (هذه الفاتورة فيها {m:,}). "
                    "قم بالترقية لتحليلها."),
    "ai_own_key": ("On the free plan, add your own free Gemini key in the sidebar to use AI features.",
                   "في الخطة المجانية، أضف مفتاح Gemini المجاني الخاص بك في الشريط الجانبي لاستخدام الذكاء الاصطناعي."),
    "ai_limit": ("You've reached the AI limit for this session ({n} requests). Add your own Gemini key in "
                 "the sidebar to continue without limits.",
                 "وصلت إلى حد طلبات الذكاء الاصطناعي لهذه الجلسة ({n} طلبات). أضف مفتاح Gemini الخاص بك "
                 "في الشريط الجانبي للمتابعة بلا حدود."),
    "ai_remaining": ("{n} AI requests left this session.", "متبقٍ {n} طلبات ذكاء اصطناعي في هذه الجلسة."),
    # --- footer ----------------------------------------------------------------
    "b2b_header": ("💼 B2B & Enterprise services", "💼 خدمات الشركات والأعمال (B2B)"),
    "b2b_text": ("Need deeper cloud cost reduction? Our expert team provides end-to-end cloud audit consulting.",
                 "هل تريد تخفيضاً أكبر في تكاليف السحابة؟ يتوفر فريقنا المتخصص لتقديم استشارات وتدقيق شامل لشركتك."),
    "b2b_contact": ("📩 Contact us for an audit session:", "📩 للتواصل وحجز جلسة تدقيق:"),
}


def tr(key: str, lang: str, **kwargs):
    en, ar = _T[key]
    value = ar if lang == AR else en
    return value.format(**kwargs) if kwargs and isinstance(value, str) else value
