import streamlit as st
import PyPDF2
from supabase import create_client
from datetime import datetime
import re
from google import genai

# ---------- Load secrets ----------
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    gemini_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error(f"Configuration error: Check your secrets. {e}")
    st.stop()

st.set_page_config(page_title="MarkMate", page_icon="✏️", layout="wide")
st.title("✏️ MarkMate")
st.caption("AI examiner – like a real teacher with a red pen")

# ---------- Session State ----------
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_error" not in st.session_state:
    st.session_state.auth_error = None

# ---------- Authentication Functions ----------
def sign_up(email, password):
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        if res.user:
            st.success("✅ Account created! Please check your email to confirm your account before logging in.")
            return True
        else:
            st.error("Sign up failed. Try a different email.")
            return False
    except Exception as e:
        st.error(f"Sign up error: {str(e)}")
        return False

def sign_in(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            st.session_state.user = res.user
            st.session_state.auth_error = None
            st.rerun()
        else:
            st.error("Invalid email or password.")
    except Exception as e:
        error_msg = str(e)
        if "Email not confirmed" in error_msg:
            st.error("❌ Please confirm your email first. Check your inbox (and spam) for the confirmation link.")
        else:
            st.error(f"Login failed: {error_msg}")

def sign_out():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# ---------- Sidebar Authentication UI ----------
with st.sidebar:
    st.header("Account")
    if st.session_state.user is None:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login"):
                if email and password:
                    sign_in(email, password)
                else:
                    st.warning("Please enter email and password.")
        with col2:
            if st.button("Sign Up"):
                if email and password:
                    sign_up(email, password)
                else:
                    st.warning("Please enter email and password.")
    else:
        st.write(f"✅ Logged in as: **{st.session_state.user.email}**")
        if st.button("Logout"):
            sign_out()

# ---------- Main App (Logged In) ----------
if st.session_state.user is not None:
    user_id = st.session_state.user.id

    # ---------- PDF Upload & Marking ----------
    uploaded_file = st.file_uploader("Upload your exam paper (PDF)", type=["pdf"])

    if uploaded_file is not None:
        # Read PDF text
        with st.spinner("📄 Reading your paper..."):
            try:
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
                if not text.strip():
                    st.error("⚠️ Could not extract text from this PDF. It might be a scanned image (handwriting OCR coming soon).")
                    st.stop()
            except Exception as e:
                st.error(f"Error reading PDF: {e}")
                st.stop()

        # AI Marking
        with st.spinner("✏️ AI examiner (Gemini 2.5) is marking your work..."):
            try:
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
            except Exception as e:
                st.error(f"AI marking failed: {e}")

    # ---------- Past Markings History ----------
    with st.expander("📜 Your Past Markings (last 10)"):
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
    # Not logged in – show marketing info
    st.info("👆 Please **Login** or **Sign Up** in the sidebar to start marking papers.")
    st.markdown("""
    ### ✨ What is MarkMate?
    - **AI-powered exam checking** – instant feedback like a real examiner.
    - **Red pen annotations** – coming soon.
    - **Focus clock & streaks** – coming soon.
    - **Revision hub** – coming soon.

    **Start for free – 1 check per day.**
    """)
