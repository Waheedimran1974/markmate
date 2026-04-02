import streamlit as st
import PyPDF2
import google.generativeai as genai

# Page config
st.set_page_config(page_title="MarkMate", page_icon="✏️")
st.title("✏️ MarkMate")
st.caption("AI examiner – like a real teacher with a red pen")

# Load API key from Streamlit secrets
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

uploaded_file = st.file_uploader("Upload your exam paper (PDF)", type=["pdf"])

if uploaded_file is not None:
    with st.spinner("Reading your paper..."):
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""

    if text.strip():
        with st.spinner("AI examiner is marking your work..."):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""
You are an IGCSE/A-Level examiner. Mark this student's answer.

Student's answer:
{text[:8000]}

Give feedback in this exact format:

🔴 ERRORS FOUND:
- (list specific errors)

✅ HOW TO IMPROVE:
- (specific advice)

📊 SCORE: __/10

💡 SUMMARY: (2 sentences)
"""
            response = model.generate_content(prompt)
            st.subheader("📝 Marked Paper")
            st.markdown(response.text)
            st.balloons()
    else:
        st.error("Could not read text from PDF. (Handwriting OCR coming soon.)")
else:
    st.info("Upload a PDF to get started.")
