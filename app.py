# ============================================================
#                 AI Quiz Management System
# ============================================================

import streamlit as st
import json, uuid, os, time, math, random, base64
from datetime import datetime

# ------------------ SAFE IMPORTS ------------------
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except:
    PANDAS_AVAILABLE = False
    st.warning("Pandas not available. Analytics & result tables will be disabled.")

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except:
    FPDF_AVAILABLE = False
    st.warning("FPDF not available. PDF export and certificates will be disabled.")

try:
    import textract
    TEXTRACT_AVAILABLE = True
except:
    TEXTRACT_AVAILABLE = False
    st.warning("Textract not available. Slide uploads will be disabled.")

try:
    from openrouter import OpenRouter
    OPENROUTER_API = st.secrets["openrouter"]["api_key"]
    openrouter = OpenRouter(api_key=OPENROUTER_API)
    OPENROUTER_AVAILABLE = True
except:
    OPENROUTER_AVAILABLE = False
    st.warning("OpenRouter not available. AI features will be disabled.")

# ------------------ FILES ------------------
if not os.path.exists("data"): os.makedirs("data")
QUIZ_FILE = "data/quizzes.json"
RESULT_FILE = "data/results.json"
USER_FILE = "data/users.json"

def safe_read(path, default):
    try:
        if os.path.exists(path):
            with open(path,"r") as f: return json.load(f)
    except: pass
    return default

def safe_write(path, data):
    with open(path,"w") as f: json.dump(data,f,indent=4)

def load_users(): return safe_read(USER_FILE, {})
def save_users(d): safe_write(USER_FILE,d)
def load_quizzes(): return safe_read(QUIZ_FILE,{})
def save_quizzes(d): safe_write(QUIZ_FILE,d)
def load_results(): return safe_read(RESULT_FILE,[])
def save_results(d): safe_write(RESULT_FILE,d)

# ------------------ SESSION STATE ------------------
if "logged_in" not in st.session_state: st.session_state.logged_in=False
if "username" not in st.session_state: st.session_state.username=""
if "role" not in st.session_state: st.session_state.role=""
if "current_quiz" not in st.session_state: st.session_state.current_quiz=None
if "quiz_step" not in st.session_state: st.session_state.quiz_step=0
if "answers" not in st.session_state: st.session_state.answers={}
if "quiz_started" not in st.session_state: st.session_state.quiz_started=False
if "quiz_end_time" not in st.session_state: st.session_state.quiz_end_time=None

# ------------------ STYLES ------------------
st.set_page_config(page_title="AI Quiz System", layout="wide")
st.markdown("""
<style>
body{transition:0.3s;}
.quiz-card{padding:15px;border-radius:12px;background:#f8f9fa;border:2px solid #eee;margin-bottom:15px;}
.quiz-card:hover{background:#f0f0f0;}
.stButton>button{background-color:#1a73e8;color:white;padding:10px 20px;border-radius:8px;font-size:16px;border:none;}
.stButton>button:hover{background-color:#1558b0;}
</style>
""",unsafe_allow_html=True)

# ------------------ SAFE MCQ FIX ------------------
def fix_mcq_options(mcq):
    options = mcq.get("options",[])
    answer = mcq.get("answer","").strip()
    if answer and answer not in options: options.append(answer)
    while len(options)<4: options.append(f"Option {len(options)+1}")
    mcq["options"]=options[:4]
    return mcq

# ------------------ AI MCQ GENERATION ------------------
def generate_mcqs_from_text_ai(text,num_questions=5,difficulty="Medium"):
    if not OPENROUTER_AVAILABLE:
        st.warning("OpenRouter not available")
        return []
    prompt=f"""
    Extract {num_questions} MCQs, True/False, Short Answer, Fill-in-the-Blank from the text.
    Return JSON array like: [{{"type":"MCQ|TF|Short|Fill","question":"...","options":["A","B","C","D"],"answer":"...","description":"..."}}]
    Text:
    {text}
    """
    try:
        response=openrouter.chat.send(model="google/gemma-3n-e2b-it:free",
                                      messages=[{"role":"user","content":prompt}],
                                      stream=False)
        ai_text=response.choices[0].message.get("content","")
        import json
        mcqs_raw=json.loads(ai_text)
        return [fix_mcq_options(m) for m in mcqs_raw]
    except Exception as e:
        st.error(f"AI Error: {e}")
        return []

# ------------------ CERTIFICATES ------------------
def generate_certificate(student_name, quiz_name, score):
    if not FPDF_AVAILABLE: return
    pdf = FPDF(orientation='L',unit='mm',format='A4')
    pdf.add_page()
    pdf.set_font("Arial","B",36)
    pdf.cell(0,60,"Certificate of Completion",align="C",ln=1)
    pdf.set_font("Arial","",24)
    pdf.cell(0,20,f"Awarded to: {student_name}",align="C",ln=1)
    pdf.cell(0,20,f"For completing the quiz: {quiz_name}",align="C",ln=1)
    pdf.cell(0,20,f"Score: {score}",align="C",ln=1)
    fname=f"Certificate_{student_name}_{quiz_name}.pdf"
    pdf.output(fname)
    with open(fname,"rb") as f: b64=base64.b64encode(f.read()).decode()
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{fname}">📄 Download Certificate</a>',unsafe_allow_html=True)

# ------------------ EXPORT RESULTS PDF ------------------
def export_results_pdf():
    if not FPDF_AVAILABLE or not PANDAS_AVAILABLE: return
    results=load_results()
    if not results: st.info("No results to export"); return
    df=pd.DataFrame(results)
    from fpdf import FPDF
    pdf=FPDF(); pdf.add_page(); pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"Quiz Results",ln=1,align="C"); pdf.set_font("Arial","",12)
    for i,row in df.iterrows():
        pdf.cell(0,8,f"{row['student']} | {row['quiz']} | {row['score']}",ln=1)
    fname="QuizResults.pdf"; pdf.output(fname)
    with open(fname,"rb") as f: b64=base64.b64encode(f.read()).decode()
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{fname}">📄 Download Results PDF</a>',unsafe_allow_html=True)

# ------------------ LOGIN PAGE ------------------
def login_page():
    st.title("🔐 Login")
    username=st.text_input("Username")
    password=st.text_input("Password",type="password")
    role=st.selectbox("Role",["Student","Admin"])
    if st.button("Login"):
        users=load_users()
        if role=="Admin":
            if username=="admin" and password=="admin123":
                st.session_state.logged_in=True
                st.session_state.username=username
                st.session_state.role="Admin"
                st.experimental_rerun()
            else: st.error("Invalid admin credentials")
        else:
            if username not in users:
                users[username]={"password":password}; save_users(users)
            elif users[username]["password"]!=password:
                st.error("Invalid password"); return
            st.session_state.logged_in=True
            st.session_state.username=username
            st.session_state.role="Student"
            st.experimental_rerun()

# ------------------ MAIN ROUTER ------------------
if not st.session_state.logged_in:
    login_page()
elif st.session_state.role=="Admin":
    st.info("Admin panel loading...")  # Placeholder for full admin_panel()
else:
    st.info("Student panel loading...")  # Placeholder for full student_panel()
