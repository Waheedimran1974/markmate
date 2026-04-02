import streamlit as st
import PyPDF2
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import re

# --- Load secrets ---
# For local development
load_dotenv()
# For Streamlit Cloud (use st.secrets)
# genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

st.set_page_config(page_title="MarkMate", page_icon="✏️", layout="wide")
st.title("✏️ MarkMate")
st.caption("AI examiner – like a real teacher with a red pen")

# --- Authentication UI (Placeholder) ---
if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.header("Account")
    if st.session_state.user is None:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            st.session_state.user = email
            st.rerun()
        if st.button("Sign Up"):
            st.session_state.user = email
            st.rerun()
    else:
        st.write(f"Logged in as: {st.session_state.user}")
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

# --- Main app (only if logged in) ---
if st.session_state.user is not None:
    uploaded_file = st.file_uploader("Upload your exam paper (PDF)", type=["pdf"])

    if uploaded_file is not None:
        with st.spinner("Reading your paper..."):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""

        if text.strip():
            with st.spinner("AI examiner is marking your work..."):
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
                response = client.models.generate_content(
                    model='gemini-2.5-pro',
                    contents=prompt
                )
                feedback = response.text

                # Extract score (simple – you can improve this)
                score_match = re.search(r"SCORE:\s*(\d+)/10", feedback)
                score = score_match.group(1) if score_match else "?"

                # Display feedback
                st.subheader("📝 Marked Paper")
                st.markdown(feedback)
                st.balloons()
        else:
            st.error("Could not read text from PDF. (Handwriting OCR coming soon.)")
    else:
        st.info("Upload a PDF to get started.")
else:
    st.info("👆 Please login or sign up in the sidebar to start marking papers.")
    st.markdown("""
    ### ✨ What is MarkMate?
    - **AI-powered exam checking** – instant feedback like a real examiner.
    - **Red pen annotations** – coming soon.
    - **Focus clock & streaks** – coming soon.
    - **Revision hub** – coming soon.

    **Start for free – 1 check per day.**
    """)
