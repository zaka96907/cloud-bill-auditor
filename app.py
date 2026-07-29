import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

# 1. إعداد قائمة اختيار اللغة في الشريط الجانبي أولاً
with st.sidebar:
    st.title("🌐 Language / اللغة")
    lang = st.selectbox("اختر لغة الواجهة / Choose Language", ["العربية", "English"])
    st.markdown("---")

# 2. قاموس النصوص لكلتا اللغتين (تحديث شامل مع الميزات الجديدة)
texts = {
    "العربية": {
        "dir": "rtl",
        "align": "right",
        "sidebar_title": "🔑 إعدادات الاتصال",
        "api_label": "أدخل مفتاح Gemini API السري الخاص بك:",
        "api_link": "الحصول على مفتاح مجاني",
        "title": "🕵️‍♂️ مفتش الفواتير السحابية الذكي",
        "subtitle": "اكتشف الهدر المالي في حسابات AWS و Google Cloud خلال ثوانٍ",
        "uploader_label": "قم برفع ملف الفاتورة بصيغة (CSV)",
        "checkbox_label": "⚙️ لا تملك ملفاً؟ اضغط هنا لتوليد فاتورة تجريبية وتحليلها",
        "success_upload": "✅ تم رفع ملف الفاتورة الحقيقي وقراءته بنجاح!",
        "error_upload": "❌ عذراً، هناك مشكلة في تنسيق ملف الـ CSV:",
        "info_sample": "💡 تم توليد فاتورة تجريبية للمحاكاة.",
        "data_sub": "📊 البيانات المستخرجة من الفاتورة:",
        "metric_label": "💰 إجمالي التكاليف السحابية",
        "saving_label": "💸 الهدر المالي القابل للتوفير فوراً",
        "chart_sub": "📊 تحليل التكاليف بصرياً:",
        "btn_analyze": "🔍 ابدأ تحليل الفاتورة وكشف الهدر المالي",
        "error_api": "⚠️ من فضلك، أدخل مفتاح الـ API السري في الشريط الجانبي أولاً لتفعيل الذكاء الاصطناعي!",
        "spinner": "جاري إرسال البيانات إلى Gemini وتحليلها سطراً بسطر...",
        "success_ai": "🎉 اكتمل التحليل الذكي بنجاح!",
        "expander_title": "📋 انقر هنا لعرض تقرير مفتش الفواتير الذكي بالكامل",
        "btn_download": "📥 تحميل التقرير الذكي (ملف نصي)",
        "error_gemini": "❌ حدث خطأ أثناء الاتصال بـ Gemini:",
        "prompt_role": "أنت خبير في تدقيق الحسابات السحابية ومكافحة الهدر المالي. حلل جدول الفاتورة التالي المأخوذ من خوادم سحابية، وحدد بدقة أين يكمن الهدر المالي (الخدمات الخاملة Idle أو غير المستغلة) واقترح حلولاً عملية واضحة لتوفير التكلفة باللغة العربية متبوعة بجدول ملخص:"
    },
    "English": {
        "dir": "ltr",
        "align": "left",
        "sidebar_title": "🔑 Connection Settings",
        "api_label": "Enter your secret Gemini API key:",
        "api_link": "Get a free key",
        "title": "🕵️‍♂️ Smart Cloud Bill Auditor",
        "subtitle": "Discover financial waste in AWS & Google Cloud accounts in seconds",
        "uploader_label": "Upload your bill file in (CSV) format",
        "checkbox_label": "⚙️ Don't have a file? Click here to generate a sample bill",
        "success_upload": "✅ Real bill file uploaded and parsed successfully!",
        "error_upload": "❌ Sorry, there is an issue with the CSV file format:",
        "info_sample": "💡 Sample bill generated for simulation.",
        "data_sub": "📊 Extracted Data from Bill:",
        "metric_label": "💰 Total Cloud Costs",
        "saving_label": "💸 Immediate Potential Savings",
        "chart_sub": "📊 Cost Visual Analysis:",
        "btn_analyze": "🔍 Start Bill Analysis & Detect Waste",
        "error_api": "⚠️ Please enter your secret API key in the sidebar first to enable AI!",
        "spinner": "Sending data to Gemini and analyzing line by line...",
        "success_ai": "🎉 Smart analysis completed successfully!",
        "expander_title": "📋 Click here to view the full Auditor Report",
        "btn_download": "📥 Download Smart Report (TXT File)",
        "error_gemini": "❌ An error occurred while connecting to Gemini:",
        "prompt_role": "You are an expert cloud auditor and financial waste management specialist. Analyze the following cloud billing table, pinpoint exactly where the financial waste lies (Idle or Underutilized services), and suggest practical, clear solutions to save costs. Provide your response in English followed by a summary table:"
    }
}

# اختيار النصوص بناءً على اللغة المحددة
t = texts[lang]

# 3. تحسين المظهر ودعم اتجاه النصوص ديناميكياً مع تلوين العدادات
st.markdown(f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    
    <style>
    html, body, [data-testid="stWidgetLabel"], .stApp {{
        font-family: 'Cairo', sans-serif !important;
    }}
    .stApp {{ direction: {t['dir']}; text-align: {t['align']}; }}
    
    /* لون إجمالي التكاليف (أحمر) */
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        font-size: 30px !important;
        font-weight: bold;
    }}
    </style>
    """, unsafe_allow_html=True)

# 4. محتويات الشريط الجانبي الإضافية
with st.sidebar:
    st.title(t["sidebar_title"])
    api_key = st.text_input(t["api_label"], type="password")
    st.markdown(f"[{t['api_link']}](https://aistudio.google.com/)")

# 5. الواجهة الرئيسية
st.title(t["title"])
st.subheader(t["subtitle"])

uploaded_file = st.file_uploader(t["uploader_label"], type=["csv"])
st.markdown("---")
use_sample = st.checkbox(t["checkbox_label"])

df = None

# رفع الملف الحقيقي
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, skip_blank_lines=True).dropna(how='all')
        
        rename_dict = {}
        for col in df.columns:
            col_lower = col.lower()
            if 'cost' in col_lower or 'تكلفة' in col_lower or 'المبلغ' in col_lower:
                rename_dict[col] = 'التكلفة ($)'
            elif 'provider' in col_lower or 'مورد' in col_lower or 'شركة' in col_lower:
                rename_dict[col] = 'المورد (Provider)'
            elif 'service' in col_lower or 'خدمة' in col_lower:
                rename_dict[col] = 'الخدمة (Service)'
            elif 'status' in col_lower or 'حالة' in col_lower:
                rename_dict[col] = 'الحالة (Status)'
        
        df = df.rename(columns=rename_dict)
        st.success(t["success_upload"])
    except Exception as e:
        st.error(f"{t['error_upload']} {e}")

# استخدام البيانات التجريبية
elif use_sample:
    sample_data = {
        'المورد (Provider)': ['AWS', 'AWS', 'Google Cloud', 'AWS', 'Google Cloud'],
        'الخدمة (Service)': ['EC2', 'S3', 'Compute Engine', 'RDS', 'Cloud Storage'],
        'التكلفة ($)': [450, 80, 320, 150, 45],
        'الحالة (Status)': ['Idle', 'Active', 'Underutilized', 'Active', 'Idle']
    }
    df = pd.DataFrame(sample_data)
    st.info(t["info_sample"])

# عرض البيانات والتحليل
if df is not None:
    st.subheader(t["data_sub"])
    
    # حساب إجمالي التكاليف
    total_cost = df['التكلفة ($)'].sum()
    
    # خوارزمية ذكية لحساب التوفير تلقائياً: جمع المبالغ للخدمات الخاملة أو غير المستغلة
    waste_df = df[df['الحالة (Status)'].str.lower().str.contains('idle|underutilized|خامل|غير مستغل', na=False)]
    potential_savings = waste_df['التكلفة ($)'].sum()
    
    # عرض البطاقات الرقمية بجانب بعضها البعض
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label=t["metric_label"], value=f"${total_cost:,.2f}")
    with col2:
        st.metric(label=t["saving_label"], value=f"${potential_savings:,.2f}", delta=f"-${potential_savings:,.2f}", delta_color="inverse")
        
    st.markdown("---")
    st.dataframe(df)
    st.markdown("---")
    
    st.subheader(t["chart_sub"])
    chart_data = df.groupby('المورد (Provider)')['التكلفة ($)'].sum()
    st.bar_chart(chart_data)
    st.markdown("---")
    
    if st.button(t["btn_analyze"]):
        if not api_key:
            st.error(t["error_api"])
        else:
            with st.spinner(t["spinner"]):
                try:
                    client = genai.Client(api_key=api_key)
                    data_string = df.to_string(index=False)
                    prompt = f"{t['prompt_role']}\n\n{data_string}"
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )
                    
                    st.success(t["success_ai"])
                    with st.expander(t["expander_title"], expanded=True):
                        st.markdown(response.text)
                        
                        # زر تحميل التقرير الذكي كملف نصي مدمج داخل الصندوق
                        st.download_button(
                            label=t["btn_download"],
                            data=response.text,
                            file_name="cloud_audit_report.txt",
                            mime="text/plain"
                        )
                    
                except Exception as e:
                    st.error(f"{t['error_gemini']} {e}")
                    # --- قسم الخدمات المدفوعة للشركات ---
st.sidebar.markdown("---")
st.sidebar.subheader("💼 خدمات الشركات والأعمال (B2B)")
st.sidebar.info(
    "هل تريد تحليلاً شاملاً وتوفير تكاليف السحاب لشركتك؟"
)
st.sidebar.markdown("📧 **لطلب خدمة مخصصة:**\nتواصل معنا عبر البريد الإكتروني مباشرة.")
