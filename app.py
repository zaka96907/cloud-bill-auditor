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
    """
    تنظيف البيانات وحساب إجمالي الإنفاق، أعلى الخدمات، والقفزات محلياً
    """
    try:
        df_clean = df.copy()
        df_clean.columns = df_clean.columns.str.strip()
        
        # البحث عن عمود التكلفة وعمود الخدمة تلقائياً
        cost_col = [c for c in df_clean.columns if any(k in c.lower() for k in ['cost', 'amount', 'unblendedcost', 'cost_usd'])]
        service_col = [c for c in df_clean.columns if any(k in c.lower() for k in ['service', 'product', 'productcode'])]
        
        c_name = cost_col[0] if cost_col else df_clean.columns[-1]
        s_name = service_col[0] if service_col else df_clean.columns[0]
        
        # تحويل القيم المالية لأرقام
        df_clean[c_name] = pd.to_numeric(df_clean[c_name], errors='coerce').fillna(0)
        
        # الحسابات
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
# دالة توليد تقرير PDF
# ---------------------------------------------------------
def generate_pdf_report(analysis_text):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, txt="Cloud Bill Audit Report", ln=1, align="C")
    pdf.ln(10)
    
    # Body Content
    pdf.set_font("Helvetica", size=10)
    
    # تنظيف النص وتصفية أي أحرف غير لاتينية
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
                    # 1. تنفيذ معالجة Pandas محلياً قبل الإرسال
                    summary = process_csv_with_pandas(df)
                    
                    # 2. بناء البرومبت بالبيانات المجهزة من Pandas
                    if summary:
                        data_summary = f"""
                        Pre-calculated Billing Summary:
                        - Total Spend: ${summary['total_spend']}
                        - Top Costliest Services: {summary['top_services']}
                        - Single Cost Spikes: {summary['spikes']}
                        
                        Full Raw Data:
                        {df.to_string()}
                        """
                    else:
                        data_summary = df.to_string()

                    client = genai.Client(api_key=api_key)
                    prompt = f"""
                    You are a Cloud Financial Operations (FinOps) Expert.
                    Analyze the following pre-processed cloud invoice data and provide a clear, professional summary with actionable cost-saving recommendations.
                    Keep the response in the same language as chosen by user ({lang}).

                    Data Summary:
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
