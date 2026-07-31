import streamlit as st
import pandas as pd
from google import genai
from fpdf import FPDF

# --------------------------------------------------
# 1. معالجة البيانات محلياً (Pandas Pre-processing)
# --------------------------------------------------
def process_csv_with_pandas(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        
        # تنظيف أسماء الأعمدة
        df.columns = df.columns.str.strip().str.lower()
        
        # البحث عن الأعمدة الأساسية
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
# 2. إنشاء تقرير PDF
# --------------------------------------------------
def generate_pdf_report(analysis_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Cloud Audit & FinOps Executive Report", ln=1, align='C')
    pdf.ln(10)
    
    # تحويل النص ليتوافق مع مكتبة FPDF
    clean_text = analysis_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    
    return pdf.output(dest='S').encode('latin-1')

# --------------------------------------------------
# 3. واجهة التطبيق (Streamlit Interface)
# --------------------------------------------------
st.set_page_config(page_title="Cloud Bill Auditor", layout="wide")
st.title("☁️ Cloud Bill Auditor & FinOps Optimizer")
st.write("قم برفع ملف فاتورة السحابة (CSV) للحصول على تحليل محلي ورقمي دقيق وتوصيات الذكاء الاصطناعي لتقليل التكاليف.")

# جلب مفتاح الـ API بأمان
api_key = st.secrets.get("GEMINI_API_KEY", "")

uploaded_file = st.file_uploader("اختر ملف الفاتورة (CSV)", type=["csv"])

if uploaded_file is not None:
    st.success("تم رفع الملف بنجاح! جاري معالجة البيانات محلياً...")
    
    # معالجة ملف Pandas محلياً
    summary, error = process_csv_with_pandas(uploaded_file)
    
    if error:
        st.error(f"حدث خطأ في قراءة الملف: {error}")
    else:
        # عرض نتائج Pandas المباشرة في الواجهة
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="إجمالي الإنفاق (Total Spend)", value=f"${summary['total_spend']}")
        
        st.subheader("📊 أعلى 5 خدمات استهلاكاً:")
        st.table(summary['top_services'])
        
        st.markdown("---")
        
        # زر تشغيل الذكاء الاصطناعي
        if st.button("🚀 تحليل التكاليف واستخراج التوصيات"):
            if not api_key:
                st.error("مفتاح GEMINI_API_KEY غير معرف في Streamlit Secrets!")
            else:
                with st.spinner("جاري تحليل التكاليف بواسطة Gemini AI..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        
                        prompt = f"""
                        You are a Cloud FinOps Expert. Analyze this pre-processed cloud cost summary:
                        
                        - Total Monthly Spend: ${summary['total_spend']}
                        - Top 5 Most Expensive Services: {summary['top_services']}
                        - Highest Cost Spikes: {summary['spikes']}
                        
                        Provide:
                        1. Executive summary of current cloud waste.
                        2. 3 concrete actions to reduce this specific spend immediately.
                        """
                        
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt
                        )
                        
                        st.subheader("💡 التقرير والتوصيات (FinOps Recommendations)")
                        st.write(response.text)
                        
                        # زر تحميل PDF
                        pdf_data = generate_pdf_report(response.text)
                        st.download_button(
                            label="📥 تحميل التقرير (PDF)",
                            data=pdf_data,
                            file_name="Cloud_Bill_Audit_Report.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"حدث خطأ أثناء التواصل مع Gemini: {e}")
