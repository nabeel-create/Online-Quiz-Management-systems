import streamlit as st
import os, json, uuid, time, math, random
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from streamlit_autorefresh import st_autorefresh

# ---------------------------
# DATA FILES
# ---------------------------
if not os.path.exists("data"): os.makedirs("data")
QUIZ_FILE   = "data/quizzes.json"
RESULT_FILE = "data/results.json"
LOGO_FILE   = "data/logo.png"

def load_json(path, default={}):
    if not os.path.exists(path): return default
    try:
        with open(path,"r") as f: return json.load(f)
    except: return default

def save_json(path,data):
    with open(path,"w") as f: json.dump(data,f,indent=4)

quizzes = load_json(QUIZ_FILE,{})
results = load_json(RESULT_FILE,{})

# ---------------------------
# SESSION STATE
# ---------------------------
ss = st.session_state
ss.setdefault("logged_in", False)
ss.setdefault("quiz_started", False)
ss.setdefault("question_index", 0)
ss.setdefault("answers", {})
ss.setdefault("start_time", None)
ss.setdefault("theme", "light")
ss.setdefault("consecutive_correct", 0)
ss.setdefault("points", 0)

# ---------------------------
# DARK MODE
# ---------------------------
if st.button("Toggle Dark/Light Theme"):
    ss.theme = "dark" if ss.theme=="light" else "light"
if ss.theme=="dark":
    st.markdown("<body class='dark'>", unsafe_allow_html=True)

# ---------------------------
# TIMER SVG (Live)
# ---------------------------
def circular_timer(seconds_left, total_seconds, container):
    pct = seconds_left/total_seconds
    radius = 80
    color = "#4CAF50" if pct>0.2 else "#FF0000"
    svg = f"""
    <svg width="200" height="200">
      <circle cx="100" cy="100" r="{radius}" fill="none" stroke="#eee" stroke-width="15"/>
      <circle cx="100" cy="100" r="{radius}" fill="none" stroke="{color}" stroke-width="15"
        stroke-dasharray="{2*math.pi*radius*pct}, {2*math.pi*radius}"/>
      <text x="100" y="110" text-anchor="middle" font-size="24" fill="black">{int(seconds_left)}s</text>
    </svg>
    """
    container.markdown(svg, unsafe_allow_html=True)

# ---------------------------
# ADMIN PANEL
# ---------------------------
def admin_panel():
    st.title("👑 Admin Dashboard")
    tab1, tab2 = st.tabs(["➕ Create Quiz","📄 Quiz List"])

    # CREATE QUIZ
    with tab1:
        st.subheader("Create Quiz")
        qname = st.text_input("Quiz Name")
        tlimit = st.number_input("Time Limit (min)",1,60,5)
        neg_mark = st.number_input("Negative Mark per Wrong Answer",0,10,2)
        if st.button("Create Quiz"):
            qid=str(uuid.uuid4())
            quizzes[qid]={"name":qname,"time_limit":tlimit,"negative_mark":neg_mark,"questions":[]}
            save_json(QUIZ_FILE,quizzes)
            st.success("Quiz Created!")

    # QUIZ LIST
    with tab2:
        st.subheader("All Quizzes")
        for qid,q in quizzes.items():
            st.markdown(f"### {q['name']} | Time: {q['time_limit']} min | Negative Mark: {q.get('negative_mark',0)}")
            url=f"{st.secrets.get('APP_URL','http://localhost:8501')}?quiz={qid}"
            st.code(url)

# ---------------------------
# STUDENT QUIZ PAGE
# ---------------------------
def student_quiz_page(quiz_id):
    if quiz_id not in quizzes: st.error("Invalid Quiz"); return
    quiz = quizzes[quiz_id]
    st.title(f"📝 {quiz['name']}")
    st.info(f"Time Limit: {quiz['time_limit']} min | Negative Mark: {quiz.get('negative_mark',0)} per wrong answer")

    timer_container = st.empty()  # container for live circular timer

    if not ss.quiz_started:
        ss.name = st.text_input("Your Name")
        ss.regno = st.text_input("Registration Number")
        if st.button("Start Quiz"):
            if not ss.name or not ss.regno: st.error("Enter details"); return
            ss.quiz_started=True
            ss.start_time=time.time()
            ss.question_index=0
            ss.answers={}
            ss.consecutive_correct=0
            ss.points=0
            random.shuffle(quiz["questions"])
            for q in quiz["questions"]:
                if "options" in q: random.shuffle(q["options"])
            st.rerun()
    else:
        total_sec = quiz["time_limit"]*60
        remaining = total_sec-(time.time()-ss.start_time)
        if remaining<=0:
            st.warning("⏳ Time Over! Auto-submitting...")
            submit_quiz(quiz_id)
            return

        # LIVE CIRCULAR TIMER
        circular_timer(remaining,total_sec,timer_container)

        idx = ss.question_index
        q = quiz["questions"][idx]
        st.write(f"### Q{idx+1}/{len(quiz['questions'])}")
        st.write(q["question"])

        qtype = q.get("type","mcq")
        ans=None
        if qtype=="mcq":
            ans = st.radio("Select one:", q["options"], key=f"q{idx}")
        elif qtype=="truefalse":
            ans = st.radio("Select:", ["True","False"], key=f"q{idx}")
        else:
            ans = st.text_input("Answer:", key=f"q{idx}")
        ss.answers[idx]=ans

        col1,col2=st.columns(2)
        with col1:
            if idx>0 and st.button("⬅ Previous"): ss.question_index-=1; st.rerun()
        with col2:
            if idx<len(quiz["questions"])-1 and st.button("Next ➡"): ss.question_index+=1; st.rerun()
            elif idx==len(quiz["questions"])-1 and st.button("Submit Quiz"): submit_quiz(quiz_id)

# ---------------------------
# QUIZ SUBMISSION
# ---------------------------
def submit_quiz(quiz_id):
    quiz = quizzes[quiz_id]
    score=0
    ss.consecutive_correct=0
    ss.points=0
    neg_mark = quiz.get("negative_mark",0)

    for i,q in enumerate(quiz["questions"]):
        user_ans=str(ss.answers.get(i,"")).strip().lower()
        correct_ans=str(q["answer"]).strip().lower()
        if user_ans==correct_ans:
            score+=1
            ss.consecutive_correct+=1
            ss.points += 10 + ss.consecutive_correct*2
        else:
            ss.consecutive_correct=0
            ss.points -= neg_mark

    rid=str(uuid.uuid4())
    results[rid] = {
        "name": ss.name,
        "regno": ss.regno,
        "quiz_id": quiz_id,
        "score": score,
        "total": len(quiz["questions"]),
        "points": ss.points,
        "date": str(datetime.now()),
        "answers": ss.answers
    }
    save_json(RESULT_FILE, results)
    st.success(f"🎉 Quiz Submitted! Score: {score}/{len(quiz['questions'])} | Points: {ss.points}")
    ss.quiz_started=False

# ---------------------------
# ADMIN LOGIN
# ---------------------------
def admin_login():
    st.title("🔐 Admin Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if user=="admin" and pwd=="admin123":
            ss.logged_in=True
            st.rerun()
        else: st.error("Invalid credentials!")

# ---------------------------
# ROUTER
# ---------------------------
params = st.experimental_get_query_params()
quiz_id = params.get("quiz",[None])[0]

if quiz_id: student_quiz_page(quiz_id)
elif not ss.logged_in: admin_login()
else: admin_panel()
