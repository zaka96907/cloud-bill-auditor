import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from fpdf import FPDF
import io

# ---------------------------------------------------------
# Goal 1 & Goal 3: دالة المعالجة، كشف نوع السحابة والانحرافات
# ---------------------------------------------------------
def process_csv_with_pandas(df):
    try:
        df_clean = df.copy()
        df_clean.columns = df_clean.columns.str.strip()
        
        # 1. كشف نوع مزود السحابة (Multi-Cloud Detection)
        cols_str = ' '.join(df_clean.columns).lower()
        if 'unblendedcost' in cols_str or 'lineitem' in cols_str:
            cloud_provider = "AWS (Amazon Web Services)"
        elif 'project_id' in cols_str or 'credits' in cols_str or 'sku' in cols_str:
            cloud_provider = "Google Cloud Platform (GCP)"
        elif 'metername' in cols_str or 'subscriptionname' in cols_str or 'resourcegroup' in cols_str:
            cloud_provider = "Microsoft Azure"
        else:
            cloud_provider = "Generic Cloud / Unknown Provider"

        # البحث عن عمود التكلفة وعمود الخدمة
        cost_col = [c for c in df_clean.columns if any(k in c.lower() for k in ['cost', 'amount', 'unblendedcost', 'cost_usd'])]
        service_col = [c for c in df_clean.columns if any(k in c.lower() for k in ['service', 'product', 'productcode'])]
        
        c_name = cost_col[0] if cost_col else df_clean.columns[-1]
        s_name = service_col[0] if service_col else df_clean.columns[0]
        
        df_clean[c_name] = pd.to_numeric(df_clean[c_name], errors='coerce').fillna(0)
        
        total_spend = df_clean[c_name].sum()
        top_services = df_clean.groupby(s_name)[c_name].sum().nlargest(5).reset_index().to_dict(orient='records')
        spikes = df_clean.nlargest(3, c_name)[[s_name, c_name]].to_dict(orient='records')
        
        # 2. كشف الشذوذ والتكلفة المرتفعة غير الطبيعية (Anomaly Detection)
        mean_cost = df_clean[c_name].mean()
        std_cost = df_clean[c_name].std()
        anomalies = []
        
        if std_cost > 0:
            anomaly_df = df_clean[df_clean[c_name] > (mean_cost + 2 * std_cost)]
            for _, row in anomaly_df.iterrows():
                anomalies.append({
                    "service": str(row[s_name]),
                    "cost": float(row[c_name])
                })
        
        return {
            "total_spend": round(total_spend, 2),
            "top_services": top_services,
            "spikes": spikes,
            "cost_col": c_name,
            "service_col": s_name,
            "cloud_provider": cloud_provider,
            "anomalies": anomalies
        }
    except Exception as e:
        return None
# ---------------------------------------------------------
# M3: دالة كشف الـ Logs المفرطة (Log Flood Detector)
# ---------------------------------------------------------
def detect_log_floods(df, lang="English"):
    log_flags = []
    df_str = df.astype(str).apply(lambda x: ' '.join(x), axis=1).str.lower()
    log_keywords = 'cloudwatch|log-group|ingestion|putlogevents|verbose|error_loop|stdout'
    log_mask = df_str.str.contains(log_keywords, na=False)
    if log_mask.any():
        flood_count = log_mask.sum()
        if lang == "العربية":
            log_flags.append(f"🌊 [Log Flood Detector]: تم كشف {flood_count} من الأنشطة المتعلقة بالـ Logs المرتفعة!")
        else:
            log_flags.append(f"🌊 [Log Flood Detector]: Detected {flood_count} high-volume logging events!")
    return log_flags
# ---------------------------------------------------------
# M4: دالة توليد الرسوم البيانية التفاعلية (Visual Cost Breakdown)
# ---------------------------------------------------------
import plotly.express as px

def render_cost_visualizations(df, summary_info, lang="English"):
    if not summary_info:
        return None, None
    
    c_name = summary_info["cost_col"]
    s_name = summary_info["service_col"]
    
    service_df = df.groupby(s_name)[c_name].sum().reset_index()
    service_df = service_df.sort_values(by=c_name, ascending=False)
    
    pie_title = "توزيع التكاليف حسب الخدمة" if lang == "العربية" else "Cost Distribution by Service"
    fig_pie = px.pie(
        service_df, 
        values=c_name, 
        names=s_name, 
        title=pie_title,
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    fig_pie.update_layout(margin=dict(t=40, b=20, l=20, r=20))

    bar_title = "أعلى 5 خدمات استهلاكاً" if lang == "العربية" else "Top 5 Cost-Consuming Services"
    top_services = service_df.head(5)
    fig_bar = px.bar(
        top_services, 
        x=c_name, 
        y=s_name, 
        orientation='h',
        title=bar_title,
        text_auto='.2f',
        color=c_name,
        color_continuous_scale='Reds'
    )
    fig_bar.update_layout(
        yaxis=dict(autorange="reversed"),
        margin=dict(t=40, b=20, l=20, r=20),
        coloraxis_showscale=False
    )
    
    return fig_pie, fig_bar
# ---------------------------------------------------------
# Goal 2 & Goal 3: محرك القواعد البرمجية والتنبيهات
# ---------------------------------------------------------
def apply_finops_rules(df, summary_info=None, lang="English"):
    flags = []
    df_str = df.astype(str).apply(lambda x: ' '.join(x), axis=1).str.lower()
    
    # القاعدة 1: كشف الموارد المتروكة
    idle_mask = df_str.str.contains('unused|idle|unattached|orphan|stopped', na=False)
    if idle_mask.any():
        idle_count = idle_mask.sum()
        if lang == "العربية":
            flags.append(f"⚠️ تم كشف {idle_count} من الموارد المتروكة أو غير المستغلة (Unused/Idle Resources).")
        else:
            flags.append(f"⚠️ Detected {idle_count} unused or idle resources (Unused/Idle Resources).")

    # القاعدة 2: كشف النسخ الاحتياطية والتخزين
    storage_mask = df_str.str.contains('storage|snapshot|backup', na=False)
    if storage_mask.any():
        if lang == "العربية":
            flags.append("ℹ️ توجد تكاليف متكررة للنسخ الاحتياطية والتخزين قد تحتاج لمراجعة سياسة الاحتفاظ.")
        else:
            flags.append("ℹ️ Recurring storage/snapshot costs detected. Consider reviewing retention policies.")

    # القاعدة 3: كشف تركز التكلفة أكثر من 40% والشذوذ
    if summary_info and summary_info['total_spend'] > 0:
        for item in summary_info['top_services']:
            service_cost = list(item.values())[1] if len(item.values()) > 1 else 0
            if (service_cost / summary_info['total_spend']) >= 0.4:
                service_name = list(item.values())[0]
                if lang == "العربية":
                    flags.append(f"🚨 تنبيه تركز التكلفة: الخدمة ({service_name}) تستهلك وحدها أكثر من 40% من إجمالي الفاتورة!")
                else:
                    flags.append(f"🚨 Cost Concentration Alert: Service ({service_name}) accounts for over 40% of the total bill!")
                    
        # تنبيه الشذوذ الانحرافي
        if summary_info.get('anomalies'):
            for anom in summary_info['anomalies']:
                if lang == "العربية":
                    flags.append(f"📈 قفزة تكلفة شاذة (Anomaly Detected): الخدمة ({anom['service']}) تكلفتها ${anom['cost']} وتتجاوز المعدل الطبيعي بشكل ملحوظ!")
                else:
                    flags.append(f"📈 Cost Anomaly Detected: Service ({anom['service']}) cost ${anom['cost']} which significantly deviates from normal patterns!")
# M3: Log Flood Check
    log_alerts = detect_log_floods(df, lang=lang)
    flags.extend(log_alerts)
    return flags

# ---------------------------------------------------------
# Goal 4: دالة توليد تقرير PDF المطور والكامل
# ---------------------------------------------------------
def generate_pdf_report(analysis_text):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, txt="Cloud Audit & FinOps Action Plan Report", ln=1, align="C")
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
        "subtitle": "اكتشف الهدر المالي واحصل على خطة توفير تنفيذية لـ AWS و GCP و Azure",
        "uploader_label": "قم برفع ملف الفاتورة بصيغة (CSV)",
        "sample_checkbox": "لا تملك ملفاً؟ اضغط هنا لتوليد فاتورة تجريبية وتحليلها ⚙️",
        "sample_success": "تم توليد بيانات فاتورة تجريبية بنجاح!",
        "btn_analyze": "🔍 بدء تحليل الفاتورة وإنشاء خطة التوفير",
        "warning_api": "يرجى إدخال مفتاح API أولاً من الشريط الجانبي للبدء.",
        "status_analyzing": "جاري تحليل الفاتورة وصياغة التوصيات وخطة العمل...",
        "results_title": "📊 التقرير النهائي وخطة العمل التنفيذية (FinOps Action Plan):",
        "rules_title": "⚡ تنبيهات محرك القواعد واكتشاف الانحرافات (FinOps Rules & Anomalies):",
        "provider_detected": "☁️ نوع المنصة السحابية المكتشفة:",
        "pdf_button": "📄 تحميل تقرير التوصيات وخطة العمل (PDF)",
        "b2b_header": "💼 خدمات الشركات والأعمال (B2B)",
        "b2b_text": "هل تريد تخفيضاً أكبر في تكاليف السحاب؟ يتوفر فريقنا المتخصص لتقديم استشارات وتدقيق شامل لشركتك.",
        "b2b_contact": "📩 للتواصل وحجز جلسة تدقيق:",
        "error_503": "السيرفر يعاني من ضغط حالياً، يرجى الضغط على زر التحليل مرة أخرى بعد بضع ثوانٍ."
    },
    "English": {
        "dir": "ltr",
        "align": "left",
        "sidebar_title": "🔑 Connection Settings",
        "api_label": "Enter your Gemini API Key:",
        "api_link": "Get a Free Key",
        "title": "🕵️‍♂️ Smart Cloud Bill Auditor",
        "subtitle": "Detect financial waste & get an actionable savings plan for AWS, GCP & Azure",
        "uploader_label": "Upload your bill file (CSV)",
        "sample_checkbox": "Don't have a file? Click here to generate a sample bill and analyze it ⚙️",
        "sample_success": "Sample bill data generated successfully!",
        "btn_analyze": "🔍 Start AI Audit & Build Action Plan",
        "warning_api": "Please enter your API Key from the sidebar first to start.",
        "status_analyzing": "Analyzing invoice & constructing actionable optimization plan...",
        "results_title": "📊 Final Audit Report & Action Plan:",
        "rules_title": "⚡ Rule Engine Quick Alerts & Anomaly Detection:",
        "provider_detected": "☁️ Detected Cloud Provider:",
        "pdf_button": "📄 Download Complete Action Plan Report (PDF)",
        "b2b_header": "💼 B2B & Enterprise Services",
        "b2b_text": "Need deeper cloud cost reduction? Our expert team provides end-to-end cloud audit consulting.",
        "b2b_contact": "📩 Contact us for an audit session:",
        "error_503": "Google API is currently experiencing high demand. Please click Analyze again in a few seconds."
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

# دعم رفع وقراءة صيغ متعددة (CSV, XLSX, JSON)
uploaded_file = st.file_uploader(t["uploader_label"], type=["csv", "xlsx", "json"])

df = None

def load_data(file):
    if file is None:
        return None
    try:
        filename = file.name.lower()
        if filename.endswith('.csv'):
            return pd.read_csv(file)
        elif filename.endswith('.xlsx'):
            return pd.read_excel(file)
        elif filename.endswith('.json'):
            return pd.read_json(file)
    except Exception as e:
        st.error(f"Error reading file / خطأ في قراءة الملف: {e}")
        return None

if uploaded_file is not None:
    df = load_data(uploaded_file)
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
            # 1. المعالجة الإحصائية وكشف نوع السحابة (Goal 1 & 3)
            summary = process_csv_with_pandas(df)
            
            # عرض المزود المكتشف
            if summary and summary.get("cloud_provider"):
                st.info(f"{t['provider_detected']} **{summary['cloud_provider']}**")
# عرض الرسوم البيانية التفاعلية
            fig_pie, fig_bar = render_cost_visualizations(df, summary, lang=lang)
            if fig_pie and fig_bar:
                st.subheader("📊 التحليل البصري للتكاليف" if lang == "العربية" else "📊 Visual Cost Breakdown")
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(fig_pie, use_container_width=True)
                with col2:
                    st.plotly_chart(fig_bar, use_container_width=True)
            # 2. القواعد البرمجية واكتشاف الشذوذ (Goal 2 & 3)
            rule_flags = apply_finops_rules(df, summary_info=summary, lang=lang)
            
            if rule_flags:
                st.subheader(t["rules_title"])
                for flag in rule_flags:
                    st.warning(flag)

            with st.spinner(t["status_analyzing"]):
                try:
                    if summary:
                        data_summary = f"""
                        Pre-calculated Billing Summary:
                        - Identified Cloud Provider: {summary['cloud_provider']}
                        - Total Spend: ${summary['total_spend']}
                        - Top Costliest Services: {summary['top_services']}
                        - Single Cost Spikes: {summary['spikes']}
                        - Detected Cost Anomalies: {summary['anomalies']}
                        - Programmatic FinOps Rule Flags: {rule_flags}
                        
                        Full Raw Data:
                        {df.to_string()}
                        """
                    else:
                        data_summary = df.to_string()

                    client = genai.Client(api_key=api_key)
                    
                    # Goal 4: توجيه الـ Prompt لبناء خطة العمل وحساب التوفير
                    prompt = f"""
                    You are a Senior Cloud Financial Operations (FinOps) Specialist.
                    Analyze the pre-processed cloud bill data, detected provider, and rule alerts below.

                    Structure your output strictly in the language: {lang} with the following sections:
                    1. Executive Summary & Provider Overview
                    2. Estimated Savings & Potential ROI (Provide estimated $ or % savings based on anomalies/unused resources)
                    3. Prioritized Step-by-Step Action Plan:
                       - High Priority / Quick Wins (Immediate actions to stop waste)
                       - Medium Priority (Optimization, commitment plans, rightsizing)
                       - Long-term Governance Policies
                    
                    Data Summary & System Alerts:
                    {data_summary}
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    
                    st.markdown(f"### {t['results_title']}")
                    result_text = response.text
                    st.write(result_text)
                    
                    pdf_bytes = generate_pdf_report(result_text)
                    st.download_button(
                        label=t["pdf_button"],
                        data=pdf_bytes,
                        file_name="Cloud_Bill_Audit_Report.pdf",
                        mime="application/pdf"
                    )
                    
                except Exception as e:
                    if "503" in str(e):
                        st.error(t["error_503"])
                    else:
                        st.error(f"Error: {e}")

st.markdown("---")
st.subheader(t["b2b_header"])
st.write(t["b2b_text"])
st.info(f"{t['b2b_contact']} support@cloudauditor.com")
