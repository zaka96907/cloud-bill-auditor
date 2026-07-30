import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from fpdf import FPDF
import io

# ---------------------------------------------------------
# دالة توليد تقرير PDF
# ---------------------------------------------------------
def generate_pdf_report(analysis_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    # Header
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(200, 10, txt="Cloud Bill Audit Report", ln=1, align="C")
    pdf.ln(10)
    
    # Body Content
    pdf.set_font("Helvetica", size=10)
    clean_text = analysis_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=clean_text)
    
    # ارجاع البيانات مباشرة بدون encode إضافي
    return bytes(pdf.output())

# ---------------------------------------------------------
# إعداد قائمة اختيار اللغة في الشريط الجانبي أولاً
# ---------------------------------------------------------
with st.sidebar:
    st.title("🌐 Language / اللغة")
    lang = st.selectbox("اختر لغة الواجهة / Choose Language", ["العربية", "English"])
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
    api_key = st.text_input(t["api_label"], type="password")
    st.markdown(f"[{t['api_link']}](https://aistudio.google.com/app/apikey)")

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
                    client = genai.Client(api_key=api_key)
                    prompt = f"""
                    You are a Cloud Financial Operations (FinOps) Expert.
                    Analyze the following cloud invoice data and provide a clear, professional summary with actionable cost-saving recommendations.
                    Keep the response in the same language as chosen by user ({lang}).

                    Data:
                    {df.to_string()}
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
