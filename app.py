# ============================================================
#                 AI Quiz Management System
#                   Author: Nabeel
# ============================================================

import streamlit as st
import json, uuid, os, time, math, random, base64
from datetime import datetime
import pandas as pd
import altair as alt

# For PDF certificates & results
from fpdf import FPDF

# For Slide / PDF text extraction
import textract

# OpenRouter AI
try:
    from openrouter import OpenRouter
    OPENROUTER_API = st.secrets["openrouter"]["api_key"]
    openrouter = OpenRouter(api_key=OPENROUTER_API)
    OPENROUTER_AVAILABLE = True
except:
    OPENROUTER_AVAILABLE = False

# ============================================================
#                  FILES & STORAGE
# ============================================================
if not os.path.exists("data"):
    os.makedirs("data")

QUIZ_FILE = "data/quizzes.json"
RESULT_FILE = "data/results.json"
USER_FILE = "data/users.json"

def safe_read(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except:
        pass
    return default

def safe_write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def load_users(): return safe_read(USER_FILE, {})
def save_users(d): safe_write(USER_FILE, d)
def load_quizzes(): return safe_read(QUIZ_FILE, {})
def save_quizzes(d): safe_write(QUIZ_FILE, d)
def load_results(): return safe_read(RESULT_FILE, [])
def save_results(d): safe_write(RESULT_FILE, d)

# ============================================================
#                  STREAMLIT PAGE SETTINGS
# ============================================================
st.set_page_config(page_title="AI Quiz System", layout="wide")

# ============================================================
#                  GLOBAL CSS & DARK MODE
# ============================================================
def apply_styles():
    st.markdown("""
    <style>
    body { transition: 0.3s; }
    .quiz-card { padding:15px; border-radius:12px; background:#f8f9fa; border:2px solid #eee; margin-bottom:15px; }
    .quiz-card:hover { background:#f0f0f0; }
    .dark .quiz-card { background:#2e2e2e; color:white; }
    .stButton>button { background-color:#1a73e8; color:white; padding:10px 20px; border-radius:8px; font-size:16px; border:none; }
    .stButton>button:hover { background-color:#1558b0; }
    .card { background:white; padding:20px; border-radius:12px; box-shadow:0 4px 10px rgba(0,0,0,0.08); text-align:center; margin-bottom:15px; }
    .card h2 { font-size:32px; color:#1a73e8; }
    .card p { font-size:18px; margin-top:-10px; }
    </style>
    """, unsafe_allow_html=True)

apply_styles()

if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False

dark_toggle = st.sidebar.checkbox("🌙 Dark Mode", st.session_state["dark_mode"])
st.session_state["dark_mode"] = dark_toggle
if dark_toggle:
    st.markdown("<body class='dark'>", unsafe_allow_html=True)

# ============================================================
#                  SESSION STATE
# ============================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "role" not in st.session_state: st.session_state.role = ""
if "current_quiz" not in st.session_state: st.session_state.current_quiz = None
if "quiz_step" not in st.session_state: st.session_state.quiz_step = 0
if "answers" not in st.session_state: st.session_state.answers = {}
if "quiz_started" not in st.session_state: st.session_state.quiz_started = False
if "quiz_end_time" not in st.session_state: st.session_state.quiz_end_time = None

# ============================================================
#                  UTILITY FUNCTIONS
# ============================================================
def fix_mcq_options(mcq):
    options = mcq.get("options", [])
    answer = mcq.get("answer", "").strip()
    if answer and answer not in options: options.append(answer)
    while len(options)<4: options.append(f"Option {len(options)+1}")
    options = options[:4]
    mcq["options"] = options
    return mcq

def generate_mcqs_from_text_ai(text, num_questions=5, difficulty="Medium"):
    if not OPENROUTER_AVAILABLE:
        st.error("OpenRouter not available")
        return []
    prompt = f"""
    Extract {num_questions} multiple-choice questions (MCQs), True/False, Short Answer, and Fill-in-the-Blank questions from the following text.
    Each question must have a difficulty: {difficulty}.
    STRICTLY return JSON array like:
    [
      {{
        "type":"MCQ|TF|Short|Fill",
        "question":"...",
        "options":["A","B","C","D"], 
        "answer":"...",
        "description":"..."
      }}
    ]
    Text:
    {text}
    """
    try:
        response = openrouter.chat.send(
            model="google/gemma-3n-e2b-it:free",
            messages=[{"role":"user","content":prompt}],
            stream=False
        )
        ai_text = response.choices[0].message.get("content","")
        mcqs_raw = json.loads(ai_text)
        fixed = [fix_mcq_options(m) for m in mcqs_raw]
        return fixed
    except Exception as e:
        st.error(f"AI Error: {e}")
        return []

# ============================================================
#                  CERTIFICATES / PDF
# ============================================================
def generate_certificate(student_name, quiz_name, score):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", "B", 36)
    pdf.cell(0, 60, "Certificate of Completion", align="C", ln=1)
    pdf.set_font("Arial", "", 24)
    pdf.cell(0, 20, f"Awarded to: {student_name}", align="C", ln=1)
    pdf.cell(0, 20, f"For completing the quiz: {quiz_name}", align="C", ln=1)
    pdf.cell(0, 20, f"Score: {score}", align="C", ln=1)
    file_name = f"Certificate_{student_name}_{quiz_name}.pdf"
    pdf.output(file_name)
    with open(file_name,"rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{file_name}">📄 Download Certificate</a>', unsafe_allow_html=True)

def export_results_pdf():
    results = load_results()
    if not results:
        st.info("No results to export")
        return
    df = pd.DataFrame(results)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"Quiz Results",ln=1,align="C")
    pdf.set_font("Arial","",12)
    for i,row in df.iterrows():
        pdf.cell(0,8,f"{row['student']} | {row['quiz']} | {row['score']}", ln=1)
    file_name="QuizResults.pdf"
    pdf.output(file_name)
    with open(file_name,"rb") as f:
        b64=base64.b64encode(f.read()).decode()
    st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{file_name}">📄 Download Results PDF</a>', unsafe_allow_html=True)

# ============================================================
#                  ADMIN PANEL
# ============================================================
def admin_panel():
    st.title(f"👑 Admin Dashboard ({st.session_state.username})")
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "➕ Create Quiz","📄 Quiz List","🧠 AI MCQ Generator",
        "📊 Results","📈 Analytics","🏆 Leaderboard","📚 Question Bank"
    ])

    quizzes = load_quizzes()
    results = load_results()
    users = load_users()

    # ------------------- Create Quiz -------------------
    with tab1:
        st.subheader("Create New Quiz")
        name = st.text_input("Quiz Name", key="new_quiz_name")
        time_limit = st.number_input("Time Limit (minutes)",1,120,5,key="new_quiz_time")
        if st.button("Create Quiz",key="create_quiz_btn"):
            if not name: st.error("Enter name")
            else:
                qid = str(uuid.uuid4())
                quizzes[qid] = {"name":name,"time_limit":time_limit,"questions":[]}
                save_quizzes(quizzes)
                st.success("Quiz Created!")

    # ------------------- Quiz List -------------------
    with tab2:
        st.subheader("All Quizzes")
        search = st.text_input("Search Quiz", key="search_quiz")
        filtered = {k:v for k,v in quizzes.items() if search.lower() in v["name"].lower()} if search else quizzes
        for qid,qdata in filtered.items():
            st.markdown(f"<div class='quiz-card'><b>{qdata['name']}</b><br>Time: {qdata['time_limit']} min<br>Questions: {len(qdata['questions'])}</div>", unsafe_allow_html=True)
        # Delete quiz
        if filtered:
            del_q = st.selectbox("Delete Quiz", list(filtered.keys()), key="del_quiz_select")
            if st.button("Delete Selected Quiz", key="del_quiz_btn"):
                if del_q in quizzes: del quizzes[del_q]; save_quizzes(quizzes); st.success("Deleted"); st.experimental_rerun()

    # ------------------- AI MCQ Generator -------------------
    with tab3:
        st.subheader("AI-Powered Quiz Generator")
        if not quizzes: st.info("Create a quiz first"); return
        selected = st.selectbox("Select Quiz", list(quizzes.keys()), format_func=lambda x: quizzes[x]["name"], key="ai_select_quiz")
        text_input = st.text_area("Paste text / lecture",height=250,key="ai_text")
        num = st.number_input("Number of Questions",1,50,5,key="ai_num_q")
        difficulty = st.selectbox("Difficulty", ["Easy","Medium","Hard"], key="ai_diff")
        if st.button("Generate Questions",key="ai_generate_btn"):
            if text_input:
                mcqs = generate_mcqs_from_text_ai(text_input,num,difficulty)
                if mcqs:
                    quizzes[selected]["questions"].extend(mcqs)
                    save_quizzes(quizzes)
                    st.success(f"{len(mcqs)} questions added!")

    # ------------------- Results -------------------
    with tab4:
        st.subheader("Student Submissions")
        if results:
            df = pd.DataFrame(results)
            st.dataframe(df)
            export_results_pdf()
        else: st.info("No results yet")

    # ------------------- Analytics -------------------
    with tab5:
        st.subheader("Analytics")
        if results:
            df = pd.DataFrame(results)
            chart = alt.Chart(df).mark_bar().encode(x="quiz_id:N", y="score:Q", tooltip=["student","quiz","score"])
            st.altair_chart(chart,use_container_width=True)
        else: st.info("No data yet")

    # ------------------- Leaderboard -------------------
    with tab6:
        st.subheader("Leaderboard")
        if results:
            df = pd.DataFrame(results)
            quiz_list = df['quiz_id'].unique()
            selected_quiz = st.selectbox("Select Quiz", quiz_list,key="leaderboard_select")
            df_quiz = df[df['quiz_id']==selected_quiz].sort_values(by="score",ascending=False)
            st.table(df_quiz[['student','score']])
        else: st.info("No results yet")

    # ------------------- Question Bank -------------------
    with tab7:
        st.subheader("Question Bank")
        bank = []
        for qid,qdata in quizzes.items():
            for q in qdata["questions"]:
                bank.append({"quiz":qdata["name"], "type":q.get("type","MCQ"), "question":q["question"], "answer":q["answer"]})
        if bank:
            df = pd.DataFrame(bank)
            st.dataframe(df)
        else: st.info("No questions yet")

# ============================================================
#                  STUDENT PANEL
# ============================================================
def student_panel():
    st.title(f"📝 Welcome {st.session_state.username}")
    quizzes = load_quizzes()
    results = load_results()
    users = load_users()
    menu = st.sidebar.radio("Go To", ["Available Quizzes","My Results","AI Chat Tutor","Upload Slides → MCQs"])

    if menu=="Available Quizzes":
        if not quizzes: st.info("No quizzes available"); return
        selected = st.selectbox("Select Quiz", list(quizzes.keys()), format_func=lambda x: quizzes[x]["name"], key="student_select_quiz")
        quiz = quizzes[selected]
        st.info(f"Time Limit: {quiz['time_limit']} min")

        if not st.session_state.quiz_started or st.session_state.current_quiz != selected:
            name = st.session_state.username
            if st.button("Start Quiz"):
                st.session_state.current_quiz = selected
                st.session_state.quiz_started = True
                st.session_state.quiz_step = 0
                st.session_state.answers = {}
                st.session_state.quiz_end_time = time.time() + quiz["time_limit"]*60
                questions = quiz["questions"][:]
                random.shuffle(questions)
                for q in questions:
                    if "options" in q: random.shuffle(q["options"])
                st.session_state.shuffled_questions = questions
                st.experimental_rerun()
        else:
            questions = st.session_state.shuffled_questions
            remaining = int(st.session_state.quiz_end_time - time.time())
            if remaining<=0:
                st.error("Time's up! Submitting...")
                st.session_state.quiz_step = len(questions)
            st.warning(f"⏳ Time Remaining: {remaining} sec")

            idx = st.session_state.quiz_step
            if idx < len(questions):
                q = questions[idx]
                st.write(f"Q{idx+1}/{len(questions)}: {q['question']}")
                if q["type"]=="MCQ":
                    choice = st.radio("", q["options"], key=f"q{idx}")
                    st.session_state.answers[idx] = choice
                elif q["type"]=="TF":
                    choice = st.radio("", ["True","False"], key=f"q{idx}")
                    st.session_state.answers[idx] = choice
                else:
                    answer = st.text_input("Answer", key=f"q{idx}")
                    st.session_state.answers[idx] = answer

                col1,col2 = st.columns(2)
                with col1:
                    if idx>0 and st.button("⬅ Previous", key=f"prev_{idx}"): st.session_state.quiz_step-=1; st.experimental_rerun()
                with col2:
                    if idx<len(questions)-1 and st.button("Next ➡", key=f"next_{idx}"): st.session_state.quiz_step+=1; st.experimental_rerun()
                    elif idx==len(questions)-1 and st.button("Submit Quiz"):
                        score=0
                        for i,q in enumerate(questions):
                            if str(st.session_state.answers.get(i,"")).strip().lower() == str(q["answer"]).strip().lower():
                                score+=1
                        rid=str(uuid.uuid4())
                        results.append({"id":rid,"student":st.session_state.username,"quiz":quiz["name"],"quiz_id":selected,"score":score,"date":str(datetime.now())})
                        save_results(results)
                        st.success(f"🎉 Quiz Submitted! Score: {score}/{len(questions)}")
                        generate_certificate(st.session_state.username, quiz["name"], score)
                        st.session_state.quiz_started=False

    elif menu=="My Results":
        st.subheader("📘 My Previous Results")
        my_results = [r for r in results if r["student"]==st.session_state.username]
        if my_results:
            df = pd.DataFrame(my_results)
            st.table(df)
        else:
            st.info("No quiz attempts yet")

    elif menu=="AI Chat Tutor":
        st.subheader("🤖 AI Chat Tutor")
        user_input = st.text_area("Ask a question about your quiz or topic")
        if st.button("Ask AI", key="ai_chat_btn"):
            if user_input.strip()=="":
                st.warning("Enter a question")
            else:
                try:
                    response = openrouter.chat.send(
                        model="google/gemma-3n-e2b-it:free",
                        messages=[{"role":"user","content":user_input}],
                        stream=False
                    )
                    answer = response.choices[0].message.get("content","")
                    st.success("AI Response:")
                    st.write(answer)
                except Exception as e:
                    st.error(f"AI Error: {e}")

    elif menu=="Upload Slides → MCQs":
        st.subheader("Upload Slides / PDF to generate MCQs")
        uploaded_file = st.file_uploader("Upload Slide / PDF", type=["pdf","pptx"])
        if uploaded_file and OPENROUTER_AVAILABLE:
            text = textract.process(uploaded_file).decode("utf-8")
            num_questions = st.number_input("Number of MCQs",1,50,5,key="slide_num_q")
            difficulty = st.selectbox("Difficulty",["Easy","Medium","Hard"], key="slide_diff")
            quizzes = load_quizzes()
            if not quizzes: st.info("Create quiz first"); return
            selected = st.selectbox("Select Quiz to add", list(quizzes.keys()), key="slide_select_quiz")
            if st.button("Generate MCQs from Slides", key="slide_generate_btn"):
                mcqs = generate_mcqs_from_text_ai(text,num_questions,difficulty)
                if mcqs:
                    quizzes[selected]["questions"].extend(mcqs)
                    save_quizzes(quizzes)
                    st.success(f"{len(mcqs)} questions added from slides!")

# ============================================================
#                  LOGIN PAGE
# ============================================================
def login_page():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Student","Admin"])
    if st.button("Login"):
        if role=="Admin":
            if username=="admin
