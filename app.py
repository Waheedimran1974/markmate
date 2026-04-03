import streamlit as st
import PyPDF2
from supabase import create_client
from datetime import datetime
import re
from google import genai

# ---------- Load secrets ----------
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
gemini_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="MarkMate", page_icon="✏️", layout="wide")
st.title("✏️ MarkMate")
st.caption("AI examiner – like a real teacher with a red pen")

# ---------- Authentication UI ----------
if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.header("Account")
    if st.session_state.user is None:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
        with col2:
            if st.button("Sign Up"):
                try:
                    res = supabase.auth.sign_up({"email": email, "password": password})
                    st.success("Account created! Please check your email to confirm.")
                except Exception as e:
                    st.error(f"Sign up failed: {e}")
    else:
        st.write(f"✅ Logged in as: {st.session_state.user.email}")
        if st.button("Logout"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# ---------- Main app (only logged in) ----------
if st.session_state.user is not None:
    user_id = st.session_state.user.id

    uploaded_file = st.file_uploader("Upload your exam paper (PDF)", type=["pdf"])

    if uploaded_file is not None:
        with st.spinner("Reading your paper..."):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""

        if text.strip():
            with st.spinner("AI examiner (Gemini 2.5) is marking your work..."):
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
                # Using Gemini 2.5 Flash (fast, cost-efficient)
                response = gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                feedback = response.text

                # Extract score
                score_match = re.search(r"SCORE:\s*(\d+)/10", feedback)
                score = score_match.group(1) if score_match else "?"

                # Save to Supabase
                supabase.table("markings").insert({
                    "user_id": user_id,
                    "filename": uploaded_file.name,
                    "extracted_text": text[:500],
                    "ai_feedback": feedback,
                    "score": score,
                    "created_at": datetime.utcnow().isoformat()
                }).execute()

                st.subheader("📝 Marked Paper")
                st.markdown(feedback)
                st.balloons()
        else:
            st.error("Could not read text from PDF. (Handwriting OCR coming soon.)")
    else:
        st.info("Upload a PDF to get started.")

    # ---------- User history ----------
    with st.expander("📜 Your Past Markings"):
        try:
            history = supabase.table("markings").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(10).execute()
            if history.data:
                for item in history.data:
                    st.markdown(f"**{item['filename']}** – Score: {item['score']}/10 – {item['created_at'][:10]}")
                    with st.expander("View feedback"):
                        st.markdown(item["ai_feedback"])
            else:
                st.info("No past markings yet. Upload a paper to get started!")
        except Exception as e:
            st.error(f"Could not load history: {e}")

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
