# 🕵️ Cloud Bill Auditor — مفتش الفواتير السحابية الذكي

يحلل فواتير **AWS و Google Cloud و Azure**، ويكتشف الهدر المالي، ويحسب **مبلغ التوفير بالدولار لكل بند**، ثم يبني خطة FinOps تنفيذية، مع تقرير وتحليل بالذكاء الاصطناعي (Gemini).

🔗 **جرّب التطبيق مباشرة:** [إضغط هنا لتشغيل التطبيق](https://cloud-bill-auditor-dkfoj46cszrepbeywpe2bu.streamlit.app)

> يعمل التدقيق والرسوم البيانية والتصدير **بدون أي مفتاح API**. مفتاح Gemini مطلوب فقط لتقرير الذكاء الاصطناعي والمحادثة.

---

## ✨ المميزات

### 📥 قراءة أي فاتورة
- **كشف تلقائي للمزود**: AWS (CUR / Cost Explorer) و GCP (Billing export) و Azure (Cost details) وأي ملف CSV عام.
- **كشف تلقائي للأعمدة**: التكلفة، الخدمة، التاريخ، المنطقة، المورد، نوع الاستخدام، الحساب/المشروع، الوسوم (Tags)، مع إمكانية تعديلها يدوياً.
- **صيغ متعددة**: CSV و CSV.GZ و ZIP و XLSX و JSON و Parquet، مع دعم ملفات بفاصلة منقوطة `;`.
- **رفع عدة ملفات (أشهر) معاً** للمقارنة الشهرية.
- **فواتير تجريبية واقعية** لكل مزود (30 يوماً) تحتوي على هدر متعمد لعرض كل المميزات.

### 💰 محرك التوفير (13 قاعدة FinOps)
| القاعدة | التوفير المقدّر |
|---|---|
| موارد خاملة / متوقفة / غير مرتبطة | 100% |
| موارد مستغلة جزئياً (يقرأ "Unused 80%" أو "CPU 12%") | حسب نسبة الاستغلال |
| بيئات تطوير واختبار تعمل 24/7 | 60% (جدولة الإيقاف) |
| أحمال قابلة للمقاطعة على On-Demand (Batch, EMR, CI…) | 50% (Spot) |
| استخدام ثابت بدون Savings Plans / RI / CUD | 28% |
| أجيال خوادم قديمة (t2, m4, n1, Dv2…) | 15% |
| GPU مرتفع التكلفة | 25% |
| عناوين IP عامة | 50% |
| نقل البيانات و NAT Gateway | 25% |
| سجلات Logs مفرطة | 35% |
| اللقطات والنسخ الاحتياطية | 30% |
| طبقات تخزين مرتفعة / gp2 | 20% |
| أحجام خوادم كبيرة جداً | 20% |

- **لا يوجد احتساب مزدوج**: إذا انطبقت عدة قواعد على نفس البند، تُحتسب الأفضل فقط.
- لكل ملاحظة: الأولوية، درجة الثقة، التكلفة المتأثرة، أهم الموارد، والإجراء الموصى به.
- يمكن تفعيل/تعطيل أي قاعدة من الشريط الجانبي.

### 🚨 الانحرافات والحوكمة
- **كشف الانحرافات اليومية** لكل خدمة باستخدام إحصاء مقاوم للقيم الشاذة (MAD) مع حساسية قابلة للتعديل.
- كشف **البنود الشاذة** المنفردة.
- تنبيهات **تركّز التكلفة** (خدمة > 40%)، **الإنفاق بدون وسوم**، و**الارتفاع الشهري**.

### 📊 لوحة تحكم تفاعلية
- مؤشرات رئيسية: إجمالي الإنفاق، التوفير المحتمل، **توقع نهاية الشهر**، معدل الإنفاق الشهري، عدد الانحرافات، نسبة الإنفاق بدون وسوم.
- رسوم: الإنفاق اليومي مع الانحرافات، التوزيع حسب الخدمة، أعلى الخدمات، الإنفاق حسب الخدمة عبر الوقت، المناطق، خريطة Treemap للخدمات والموارد، و**شلال التوفير** من الإنفاق الحالي إلى المحسّن.
- **مقارنة بالميزانية** مع مؤشر Gauge.
- **مستكشف البيانات**: فلترة حسب الخدمة/المنطقة/الحساب/التاريخ/بحث نصي، وتجميع ديناميكي، وتحميل النتائج.

### 🤖 الذكاء الاصطناعي (Gemini)
- **تقرير تنفيذي** بالبث المباشر: ملخص، جدول فرص التوفير، خطة عمل مرتّبة بالأولوية، الانحرافات، وخارطة طريق 30/60/90 يوماً.
- **"اسأل فاتورتك"**: محادثة عن الفاتورة مع اقتراحات أسئلة جاهزة.
- اختيار النموذج (2.5 Flash / Pro / Flash-Lite) وإعادة المحاولة تلقائياً عند ضغط الخوادم (503/429).
- **خصوصية**: يُرسل ملخص مجمّع فقط، وليس الفاتورة الخام.

### 📄 التصدير
- **PDF احترافي يدعم العربية بالكامل** (اتجاه من اليمين لليسار وحروف متصلة).
- **ملف Excel** متعدد الأوراق (ملخص، ملاحظات، حسب الخدمة/المنطقة/الحساب، يومي، انحرافات، كل البنود مع التوفير).
- Markdown و CSV.

### 🌐 واجهة ثنائية اللغة
- عربي (مع تخطيط RTL كامل) وإنجليزي. رابط مباشر بالعربية: `?lang=ar`.

### 🛠️ للمطورين
- واجهة سطر أوامر (CLI) وبوابة CI: `python -m auditor bill.csv --pdf report.pdf --fail-over 500`
- 40 اختباراً آلياً و GitHub Actions على Python 3.11–3.13.

---

## 🚀 التشغيل محلياً

```bash
pip install -r requirements.txt
streamlit run app.py
```

اختياري: ضع مفتاحك في `.streamlit/secrets.toml` (انظر `secrets.toml.example`) حتى لا تحتاج لإدخاله كل مرة.

### سطر الأوامر

```bash
python -m auditor --sample aws --out aws.csv
python -m auditor aws.csv --lang ar --pdf report.pdf --xlsx report.xlsx
python -m auditor aws.csv --fail-over 500   # exit code 1 if savings > $500
```

### الاختبارات

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## 💳 البيع (الخطة المجانية والاحترافية)

التطبيق جاهز للبيع بدون خادم إضافي، بنظام **رموز تفعيل**:

| | مجاني | احترافي (Pro) |
|---|---|---|
| لوحة التحكم والرسوم والانحرافات | ✅ | ✅ |
| فرص التوفير | أول 3 بالتفصيل | كلها |
| تصدير PDF و Excel و CSV | 🔒 | ✅ |
| الذكاء الاصطناعي | بمفتاح المستخدم فقط | بمفتاحك (بحد لكل جلسة) أو مفتاحه |
| حجم الفاتورة | حتى 50,000 بند | بلا حد |

**خطوات التفعيل:**
1. أنشئ رابط دفع (Stripe Payment Link أو Lemon Squeezy أو Gumroad أو PayPal).
2. ولّد رموز تفعيل:
   ```bash
   python -m auditor.licensing new-code 10
   ```
   أعطِ **CODE** للعميل بعد الدفع، وضع **HASH** في الإعدادات السرية.
3. في Streamlit Cloud ← App settings ← Secrets، الصق محتوى `.streamlit/secrets.toml.example` مع قيمك (`PRO_ACCESS_CODES` و `BUY_URL` و `PRICE_LABEL` و `GEMINI_API_KEY` و `CONTACT_EMAIL`).
4. لإلغاء عميل: احذف الـ HASH الخاص به وأعد تشغيل التطبيق.

> إذا تُركت `PRO_ACCESS_CODES` فارغة، تكون كل المميزات مفتوحة للجميع.

**الشروط والخصوصية:** [TERMS.md](TERMS.md) · [PRIVACY.md](PRIVACY.md) · الترخيص: [LICENSE](LICENSE) (ملكية خاصة، جميع الحقوق محفوظة).

## 🧱 البنية

```
app.py                 واجهة Streamlit فقط
auditor/
  parsing.py           قراءة الملفات وتوحيد الأعمدة وكشف المزود
  analytics.py         المؤشرات، الاتجاهات، التوقع، كشف الانحرافات
  rules.py             محرك قواعد FinOps وحساب التوفير
  charts.py            الرسوم البيانية (Plotly)
  ai.py                تكامل Gemini (تقرير + محادثة)
  report.py            تصدير PDF / Excel / Markdown
  samples.py           فواتير تجريبية واقعية
  licensing.py         الخطط ورموز التفعيل وحدود الاستخدام
  i18n.py              نصوص الواجهة (عربي/إنجليزي)
  __main__.py          واجهة سطر الأوامر
tests/                 الاختبارات
assets/fonts/          خط DejaVu Sans لدعم العربية في PDF
```

---

## English summary

Cloud Bill Auditor analyzes AWS, GCP and Azure billing exports, detects waste with a 13-rule FinOps engine, quantifies **per-line-item dollar savings** (never double-counted), flags anomalies with robust statistics, forecasts month-end spend, and produces an AI-written action plan with Gemini. It includes a Free/Pro plan system with access codes and a payment link, so it can be sold without a backend. It exports a fully Arabic-capable PDF, a multi-sheet Excel workbook, Markdown and CSV, and ships with a CLI, tests and CI. The audit works without any API key; Gemini is only needed for the AI report and chat.

## 💼 B2B & Enterprise

Need deeper cloud cost reduction? 📩 support@cloudauditor.com
