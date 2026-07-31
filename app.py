import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from fpdf import FPDF
import io

# ---------------------------------------------------------
# Goal 1: دالة المعالجة الأولية باستخدام Pandas
# ---------------------------------------------------------
def process_csv_with_pandas(df):
    try:
        df_clean = df.copy()
        df_clean.columns = df_clean.columns.str.strip()
        
        cost_col = [c for c in df_clean.columns if any(k in c.lower() for k in ['cost', 'amount', 'unblendedcost', 'cost_usd'])]
        service_col = [c for c in df_clean.columns if any(k in c.lower() for k in ['service', 'product', 'productcode'])]
        
        c_name = cost_col[0] if cost_col else df_clean.columns[-1]
        s_name = service_col[0] if service_col else df_clean.columns[0]
        
        df_clean[c_name] = pd.to_numeric(df_clean[c_name], errors='coerce').fillna(0)
        
        total_spend = df_clean[c_name].sum()
        top_services = df_clean.groupby(s_name)[c_name].sum().nlargest(5).reset_index().to_dict(orient='records')
        spikes = df_clean.nlargest(3, c_name)[[s_name, c_name]].to_dict(orient='records')
        
        return {
            "total_spend": round(total_spend, 2),
            "top_services": top_services,
            "spikes": spikes,
            "cost_col": c_name,
            "service_col": s_name
        }
    except Exception as e:
        return None

# ---------------------------------------------------------
# Goal 2: محرك القواعد البرمجية (FinOps Rule Engine)
# ---------------------------------------------------------
def apply_finops_rules(df):
    flags = []
    
    # دمج كامل النص في كل سطر للبحث عن الكلمات المفتاحية
    df_str = df.astype(str).apply(lambda x: ' '.join(x), axis=1).str.lower()
    
    # قاعدة 1: كشف الموارد المتروكة أو غير المستغلة (Idle / Unused Resources)
    idle_mask = df_str.str.contains('unused|idle|unattached|orphan|stopped', na=False)
    if idle_mask.any():
        idle_count = idle_mask.sum()
        flags.append(f"⚠️ تم كشف {idle_count} من الموارد المتروكة أو غير المستغلة (Unused/Idle Resources).")

    # قاعدة 2: كشف أنواع التخزين ذات التكلفة المرتفعة بدون استخدام
    storage_mask = df_str.str.contains('storage|snapshot|backup', na=False)
    if storage_mask.any():
        flags.append("ℹ️ توجد تكاليف متكررة للنسخ الاحتياطية والتخزين (Storage/Snapshots) قد تحتاج لمراجعة سياسة الاحتفاظ.")

    # قاعدة 3: كشف الخدمات التي تستهلك أكثر من 40% من إجمالي الفاتورة
    summary = process_csv_with_pandas(df)
    if summary and summary['total_spend'] > 0:
        for item in summary['top_services']:
            service_cost = list(item.values())[1] if len(item.values()) > 1 else 0
            if (service_cost / summary['total_spend']) >= 0.4:
                service_name = list(item.values())[0]
                flags.append(f"🚨 تنبيه تركز التكلفة: الخدمة ({service_name}) تستهلك وحدهـا أكثر من 40% من إجمالي الفاتورة!")

    return flags

# ---------------------------------------------------------
# دالة توليد تقرير PDF
# ---------------------------------------------------------
def generate_pdf_report(analysis_text):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, txt="Cloud Bill Audit Report", ln=1, align="C")
    pdf.ln(10)
    
    pdf.set_font("Helvetica", size=10)
    clean_text = analysis_text.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt=clean_text)
    
    return bytes(pdf.output())

# ---------------------------------------------------------
# إعداد قائمة اختيار اللغة في الشريط الجانبي أولاً
# ---------------------------------------------------------
with st.sidebar:
    st.title("🌐 Language / اللغة")
    lang = st.selectbox("Choose Language / اختر لغة الواجهة", ["English", "العربية"])
    st.markdown("---")

# ---------------------------------------------------------
# نصوص الواجهة بكلتا اللغتين
# ---------------------------------------------------------
texts = {
    "العربية": {
        "dir": "rtl",
        "align": "right",
        "sidebar_title": "🔑 إعدادات الاتصال",
        "api_label": "أدخل مفتاح Gemini API الخاص بك:",
        "api_link": "الحصول على مفتاح مجاني",
        "title": "🕵️‍♂️ مفتش الفواتير السحابية الذكي",
        "subtitle": "اكتشف الهدر المالي في حسابات Google Cloud و AWS خلال ثوانٍ",
        "uploader_label": "قم برفع ملف الفاتورة بصيغة (CSV)",
        "sample_checkbox": "لا تملك ملفاً؟ اضغط هنا لتوليد فاتورة تجريبية وتحليلها ⚙️",
        "sample_success": "تم توليد بيانات فاتورة تجريبية بنجاح!",
        "btn_analyze": "🔍 بدء تحليل الفاتورة بواسطة الذكاء الاصطناعي",
        "warning_api": "يرجى إدخال مفتاح API أولاً من الشريط الجانبي للبدء.",
        "status_analyzing": "جاري تحليل البيانات واستخراج فرص التوفير...",
        "results_title": "📊 نتائج التحليل والتوصيات:",
        "rules_title": "⚡ تنبيهات محرك القواعد السريعة (FinOps Rules):",
        "pdf_button": "📄 تحميل تقرير PDF الاحترافي",
        "b2b_header": "💼 خدمات الشركات والأعمال (B2B)",
        "b2b_text": "هل تريد تخفيضاً أكبر في تكاليف السحاب؟ يتوفر فريقنا المتخصص لتقديم استشارات وتدقيق شامل لشركتك.",
        "b2b_contact": "📩 للتواصل وحجز جلسة تدقيق:"
    },
    "English": {
        "dir": "ltr",
        "align": "left",
        "sidebar_title": "🔑 Connection Settings",
        "api_label": "Enter your Gemini API Key:",
        "api_link": "Get a Free Key",
        "title": "🕵️‍♂️ Smart Cloud Bill Auditor",
        "subtitle": "Detect financial waste in Google Cloud & AWS accounts within seconds",
        "uploader_label": "Upload your bill file (CSV)",
        "sample_checkbox": "Don't have a file? Click here to generate a sample bill and analyze it ⚙️",
        "sample_success": "Sample bill data generated successfully!",
        "btn_analyze": "🔍 Start AI Audit Analysis",
        "warning_api": "Please enter your API Key from the sidebar first to start.",
        "status_analyzing": "Analyzing data and identifying cost-saving opportunities...",
        "results_title": "📊 Audit Results & Recommendations:",
        "rules_title": "⚡ Rule Engine Quick Alerts (FinOps Rules):",
        "pdf_button": "📄 Download Professional PDF Report",
        "b2b_header": "💼 B2B & Enterprise Services",
        "b2b_text": "Need deeper cloud cost reduction? Our expert team provides end-to-end cloud audit consulting.",
        "b2b_contact": "📩 Contact us for an audit session:"
    }
}

t = texts[lang]

# ---------------------------------------------------------
# بقية إعدادات الشريط الجانبي
# ---------------------------------------------------------
with st.sidebar:
    st.title(t["sidebar_title"])
    api_key = st.secrets.get("GEMINI_API_KEY", "")

# ---------------------------------------------------------
# الواجهة الرئيسية
# ---------------------------------------------------------
st.title(t["title"])
st.write(f"### {t['subtitle']}")

uploaded_file = st.file_uploader(t["uploader_label"], type=["csv"])

df = None

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.dataframe(df.head())

use_sample = st.checkbox(t["sample_checkbox"])

if use_sample and df is None:
    sample_data = {
        "Service": ["Compute Engine", "Cloud Storage", "BigQuery", "Cloud SQL"],
        "Cost_USD": [1200.50, 450.00, 890.20, 310.00],
        "Usage_Type": ["N1-standard-8 (Unused 80%)", "Standard Storage", "Analysis Queries", "db-custom-4-16000"],
        "Region": ["us-central1", "us-east1", "us-central1", "europe-west1"]
    }
    df = pd.DataFrame(sample_data)
    st.success(t["sample_success"])
    st.dataframe(df)

if df is not None:
    if st.button(t["btn_analyze"]):
        if not api_key:
            st.warning(t["warning_api"])
        else:
            with st.spinner(t["status_analyzing"]):
                try:
                    # 1. المعالجة الإحصائية محلياً (Goal 1)
                    summary = process_csv_with_pandas(df)
                    
                    # 2. تطبيق محرك القواعد البرمجية (Goal 2)
                    rule_flags = apply_finops_rules(df)
                    
                    # عرض التنبيهات الفورية من محرك القواعد في الواجهة
                    if rule_flags:
                        st.subheader(t["rules_title"])
                        for flag in rule_flags:
                            st.warning(flag)
                    
                    # 3. بناء البرومبت المدمج لـ Gemini
                    if summary:
                        data_summary = f"""
                        Pre-calculated Billing Summary:
                        - Total Spend: ${summary['total_spend']}
                        - Top Costliest Services: {summary['top_services']}
                        - Single Cost Spikes: {summary['spikes']}
                        - Programmatic FinOps Rule Flags Detected: {rule_flags}
                        
                        Full Raw Data:
                        {df.to_string()}
                        """
                    else:
                        data_summary = df.to_string()

                    client = genai.Client(api_key=api_key)
                    prompt = f"""
                    You are a Cloud Financial Operations (FinOps) Expert.
                    Analyze the following pre-processed cloud invoice data and programmatic rule alerts.
                    Provide a clear, professional summary with actionable cost-saving recommendations based on these findings.
                    Keep the response in the same language as chosen by user ({lang}).

                    Data Summary & Alerts:
                    {data_summary}
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    
                    st.markdown(f"### {t['results_title']}")
                    result_text = response.text
                    st.write(result_text)
                    
                    # زر تحميل PDF
                    pdf_bytes = generate_pdf_report(result_text)
                    st.download_button(
                        label=t["pdf_button"],
                        data=pdf_bytes,
                        file_name="Cloud_Bill_Audit_Report.pdf",
                        mime="application/pdf"
                    )
                    
                except Exception as e:
                    st.error(f"Error: {e}")

st.markdown("---")
st.subheader(t["b2b_header"])
st.write(t["b2b_text"])
st.info(f"{t['b2b_contact']} support@cloudauditor.com")
