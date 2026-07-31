import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from fpdf import FPDF
import io

# --------------------------------------------------
# 1. دالة توليد تقرير PDF
# --------------------------------------------------
def generate_pdf_report(analysis_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, txt="Cloud Bill Audit Report", ln=1, align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", size=11)
    
    # إضافة النص للتقرير مع معالجة الرموز
    for line in analysis_text.split('\n'):
        clean_line = line.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, txt=clean_line)
        
    return bytes(pdf.output())

# --------------------------------------------------
# 2. دالة معالجة الـ CSV بـ Pandas (Pre-processing)
# --------------------------------------------------
def process_csv_with_pandas(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        
        # البحث عن أعمدة التكلفة والخدمة تلقائياً
        cost_col = [c for c in df.columns if 'cost' in c or 'amount' in c or 'unblendedcost' in c]
        service_col = [c for c in df.columns if 'service' in c or 'product' in c or 'productcode' in c]
        
        c_name = cost_col[0] if cost_col else df.columns[-1]
        s_name = service_col[0] if service_col else df.columns[0]
        
        df[c_name] = pd.to_numeric(df[c_name], errors='coerce').fillna(0)
        
        total_spend = df[c_name].sum()
        top_services = df.groupby(s_name)[c_name].sum().nlargest(5).reset_index().to_dict(orient='records')
        spikes = df.nlargest(3, c_name)[[s_name, c_name]].to_dict(orient='records')
        
        return {
            "total_spend": round(total_spend, 2),
            "top_services": top_services,
            "spikes": spikes
        }, None
    except Exception as e:
        return None, str(e)

# --------------------------------------------------
# 3. واجهة التطبيق (Streamlit Interface)
# --------------------------------------------------
st.set_page_config(page_title="Cloud Bill Auditor", layout="wide")
st.title("☁️ Cloud Bill Auditor & FinOps Optimizer")
st.write("قم برفع ملف فاتورة السحابة (CSV) للحصول على تحليل فوري وتوصيات تقليل التكاليف.")

# جلب مفتاح الـ API سرياً من Streamlit Secrets
api_key = st.secrets.get("GEMINI_API_KEY", "")

uploaded_file = st.file_uploader("اختر ملف الفاتورة (CSV)", type=["csv"])

if uploaded_file and st.button("بدء التحليل 🔍"):
    if not api_key:
        st.error("لم يتم العثور على مفتاح GEMINI_API_KEY في الإعدادات السرية (Secrets).")
    else:
        with st.spinner("جاري معالجة البيانات وتحليل الفاتورة..."):
            # الخطوة 1: المعالجة الإحصائية بـ Pandas
            summary, err = process_csv_with_pandas(uploaded_file)
            
            if err:
                st.error(f"خطأ أثناء قراءة الملف: {err}")
            else:
                # الخطوة 2: إرسال ملخص البيانات لـ Gemini
                prompt = f"""
                You are an expert Cloud FinOps Consultant. Analyze this pre-processed cloud cost summary:
                
                - Total Spend: ${summary['total_spend']}
                - Top 5 Costliest Services: {summary['top_services']}
                - Highest Single Line-Item Spikes: {summary['spikes']}
                
                Please provide:
                1. Executive Summary of the spend.
                2. Top 3 actionable recommendations to save cost immediately.
                3. Estimated potential savings percentage.
                """
                
                try:
                    # الاتصال بموديل Gemini
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    
                    analysis_result = response.text
                    
                    # عرض النتائج في الواجهة
                    st.success("تم التحليل بنجاح!")
                    st.metric("إجمالي الإنفاق", f"${summary['total_spend']}")
                    st.markdown("### 📊 تقرير الذكاء الاصطناعي والتوصيات:")
                    st.write(analysis_result)
                    
                    # زر تحميل التقرير PDF
                    pdf_bytes = generate_pdf_report(analysis_result)
                    st.download_button(
                        label="📄 تحميل التقرير PDF",
                        data=pdf_bytes,
                        file_name="cloud_audit_report.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}")
