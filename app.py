import streamlit as st
import os, json, uuid, time, math, random
import pandas as pd
import altair as alt
from datetime import datetime
from fpdf import FPDF
from PIL import Image
from streamlit_autorefresh import st_autorefresh

# ---------------------------
# DATA FOLDERS & FILES
# ---------------------------
if not os.path.exists("data"):
    os.makedirs("data")

QUIZ_FILE   = "data/quizzes.json"
RESULT_FILE = "data/results.json"
USER_FILE   = "data/users.json"
LOGO_FILE   = "data/logo.png"

def load_json(path, default={}):
    if not os.path.exists(path):
        return default
    try:
        with open(path,"r") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path,"w") as f:
        json.dump(data, f, indent=4)

quizzes = load_json(QUIZ_FILE,{})
results = load_json(RESULT_FILE,{})
users   = load_json(USER_FILE,{})

# ---------------------------
# STREAMLIT PAGE CONFIG
# ---------------------------
st.set_page_config(page_title="AI Quiz System", layout="wide")
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
# STYLE
# ---------------------------
st.markdown("""
<style>
.quiz-card {padding:15px; border-radius:12px; background:#f8f9fa; margin-bottom:15px; border:2px solid #eee;}
.quiz-card:hover {background:#f0f0f0;}
.dark .quiz-card {background:#2d2d2d; border-color:#555; color:white;}
.button-style {background-color:#4CAF50;color:white;padding:8px 16px;border-radius:6px;border:none;}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# TIMER SVG
# ---------------------------
def circular_timer(seconds_left,total_seconds):
    pct = seconds_left/total_seconds
    radius = 80
    color = "#4CAF50" if pct>0.2 else "#FF0000"
    svg=f"""
    <svg width="200" height="200">
      <circle cx="100" cy="100" r="{radius}" fill="none" stroke="#eee" stroke-width="15"/>
      <circle cx="100" cy="100" r="{radius}" fill="none" stroke="{color}" stroke-width="15"
        stroke-dasharray="{2*math.pi*radius*pct}, {2*math.pi*radius}"/>
      <text x="100" y="110" text-anchor="middle" font-size="24" fill="black">{int(seconds_left)}s</text>
    </svg>
    """
    st.markdown(svg,unsafe_allow_html=True)

# ---------------------------
# CERTIFICATE GENERATION
# ---------------------------
def generate_certificate(name,quiz_name,score,total,points):
    pdf=FPDF('P','mm','A4')
    pdf.add_page()
    width=210
    height=297
    pdf.set_line_width(2)
    color=(212,175,55)
    pdf.set_draw_color(*color)
    pdf.rect(10,10,width-20,height-20)
    if os.path.exists(LOGO_FILE):
        pdf.image(LOGO_FILE, x=width/2-30, y=20, w=60)
    pdf.set_font("Helvetica","B",26)
    pdf.ln(50)
    pdf.cell(0,20,"Certificate of Achievement",0,1,'C')
    pdf.set_font("Helvetica","B",22)
    pdf.cell(0,10,name,0,1,'C')
    pdf.set_font("Helvetica","",16)
    pdf.cell(0,10,"has successfully completed",0,1,'C')
    pdf.set_font("Helvetica","B",18)
    pdf.cell(0,10,quiz_name,0,1,'C')
    pdf.set_font("Helvetica","",14)
    pdf.cell(0,10,f"Score: {score}/{total} | Points: {points}",0,1,'C')
    percent = score/total*100
    ctype = "Bronze"
    if percent>=90: ctype="Gold"
    elif percent>=75: ctype="Silver"
    pdf.set_font("Helvetica","B",16)
    pdf.cell(0,10,f"Certificate Type: {ctype}",0,1,'C')
    pdf.cell(0,10,datetime.now().strftime("%d %B %Y"),0,1,'C')
    pdf.line(width-70,height-50,width-10,height-50)
    pdf.set_font("Helvetica","",12)
    pdf.text(width-68,height-45,"Authorized Signature")
    path=f"data/certificate_{uuid.uuid4()}.pdf"
    pdf.output(path)
    return path

# ---------------------------
# STUDENT QUIZ PAGE
# ---------------------------
def student_quiz_page(quiz_id):
    if quiz_id not in quizzes:
        st.error("Invalid Quiz")
        return
    quiz=quizzes[quiz_id]
    st.title(f"📝 {quiz['name']}")
    st.info(f"Time Limit: {quiz['time_limit']} min")
    
    if not ss.quiz_started:
        ss.name = st.text_input("Your Name")
        ss.regno = st.text_input("Registration Number")
        if st.button("Start Quiz"):
            if not ss.name or not ss.regno:
                st.error("Enter details")
                return
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
        start=ss.start_time
        total_sec=quiz["time_limit"]*60
        remaining=total_sec-(time.time()-start)
        if remaining<=0:
            st.warning("⏳ Time Over! Auto-submitting...")
            submit_quiz(quiz_id)
            return
        circular_timer(remaining,total_sec)
        idx=ss.question_index
        q=quiz["questions"][idx]
        st.progress((idx+1)/len(quiz["questions"]))
        st.write(f"### Q{idx+1}/{len(quiz['questions'])}")
        st.write(q["question"])
        qtype=q.get("type","mcq")
        ans=None
        if qtype=="mcq":
            ans=st.radio("Select one:",q["options"],key=f"q{idx}")
        elif qtype=="truefalse":
            ans=st.radio("Select:",["True","False"],key=f"q{idx}")
        else:
            ans=st.text_input("Answer:",key=f"q{idx}")
        ss.answers[idx]=ans
        col1,col2=st.columns(2)
        with col1:
            if idx>0 and st.button("⬅ Previous"): ss.question_index-=1; st.rerun()
        with col2:
            if idx<len(quiz["questions"])-1 and st.button("Next ➡"): ss.question_index+=1; st.rerun()
            elif idx==len(quiz["questions"])-1 and st.button("Submit Quiz"):
                submit_quiz(quiz_id)

# ---------------------------
# QUIZ SUBMISSION
# ---------------------------
def submit_quiz(quiz_id):
    quiz=quizzes[quiz_id]
    score=0
    ss.consecutive_correct=0
    ss.points=0
    for i,q in enumerate(quiz["questions"]):
        user_ans=str(ss.answers.get(i,"")).strip().lower()
        correct_ans=str(q["answer"]).strip().lower()
        if user_ans==correct_ans:
            score+=1
            ss.consecutive_correct+=1
            ss.points += 10 + ss.consecutive_correct*2
        else:
            ss.consecutive_correct=0
            ss.points -= 2
    rid=str(uuid.uuid4())
    results[rid]={
        "name":ss.name,
        "regno":ss.regno,
        "quiz_id":quiz_id,
        "score":score,
        "total":len(quiz["questions"]),
        "points":ss.points,
        "date":str(datetime.now())
    }
    save_json(RESULT_FILE,results)
    st.success(f"🎉 Quiz Submitted! Score: {score}/{len(quiz['questions'])} | Points: {ss.points}")
    cert_path=generate_certificate(ss.name,quiz["name"],score,len(quiz["questions"]),ss.points)
    with open(cert_path,"rb") as f:
        st.download_button("🎖 Download Certificate",f,"certificate.pdf")
    st.balloons()
    ss.quiz_started=False

# ---------------------------
# ADMIN PANEL
# ---------------------------
def admin_panel():
    st.title("👑 Admin Dashboard")
    tabs = st.tabs(["➕ Create Quiz","📄 Quiz List","📊 Results","🎓 Question Bank","🏅 Leaderboard","📤 Export"])
    
    # CREATE QUIZ
    with tabs[0]:
        st.subheader("Create Quiz")
        qname = st.text_input("Quiz Name")
        tlimit = st.number_input("Time Limit (min)",1,60,5)
        if st.button("Create Quiz"):
            qid=str(uuid.uuid4())
            quizzes[qid]={"name":qname,"time_limit":tlimit,"questions":[]}
            save_json(QUIZ_FILE,quizzes)
            st.success("Quiz Created!")
            st.text_input("Share Link:",f"{st.secrets.get('APP_URL','http://localhost:8501')}?quiz={qid}")
        st.write("---")
        st.subheader("Add Questions")
        if quizzes:
            qid = st.selectbox("Select Quiz", quizzes.keys(), format_func=lambda x: quizzes[x]["name"])
            text=st.text_input("Question")
            qtype=st.selectbox("Type",["mcq","truefalse","short","fill"])
            opts=[]
            ans=""
            if qtype=="mcq":
                opts=st.text_input("Options (comma)").split(",")
                ans=st.text_input("Correct Answer")
            elif qtype=="truefalse":
                opts=["True","False"]
                ans=st.selectbox("Correct Answer",opts)
            else:
                ans=st.text_input("Correct Answer")
            if st.button("Add Question"):
                quizzes[qid]["questions"].append({"question":text,"type":qtype,"options":opts,"answer":ans})
                save_json(QUIZ_FILE,quizzes)
                st.success("Question Added!")
        st.write("---")
        st.subheader("Upload Certificate Logo")
        logo=st.file_uploader("Upload PNG Logo", type=["png"])
        if logo:
            with open(LOGO_FILE,"wb") as f: f.write(logo.read())
            st.success("Logo Uploaded!")

    # QUIZ LIST
    with tabs[1]:
        st.subheader("All Quizzes")
        query=st.text_input("Search Quiz")
        for qid,q in quizzes.items():
            if query.lower() in q["name"].lower():
                st.markdown(f"<div class='quiz-card'>",unsafe_allow_html=True)
                st.write(f"### {q['name']}")
                st.write(f"Time: {q['time_limit']} min | Questions: {len(q['questions'])}")
                url=f"{st.secrets.get('APP_URL','http://localhost:8501')}?quiz={qid}"
                st.code(url)
                if st.button("Copy Link",key=f"copy_{qid}"): st.experimental_set_query_params(quiz=qid)
                if st.button("Delete",key=f"del_{qid}"): del quizzes[qid]; save_json(QUIZ_FILE,quizzes); st.rerun()
                st.markdown("</div>",unsafe_allow_html=True)

    # RESULTS
    with tabs[2]:
        st.subheader("Live Results")
        st_autorefresh(interval=4000)
        if results:
            df=pd.DataFrame(results).T
            st.dataframe(df)
            st.metric("Total Submissions",len(df))
        else: st.info("No results yet.")

    # QUESTION BANK
    with tabs[3]:
        st.subheader("Question Bank")
        bank=[]
        for qid,qz in quizzes.items():
            for q in qz["questions"]: bank.append(q)
        if bank: st.dataframe(pd.DataFrame(bank))
        else: st.info("No questions yet.")

    # LEADERBOARD
    with tabs[4]:
        st.subheader("Leaderboard")
        if results:
            df=pd.DataFrame(results).T
            if "points" not in df.columns: df["points"]=0
            df.sort_values("points", ascending=False, inplace=True)
            st.dataframe(df[["name","points","score","total","date"]])
        else: st.info("No submissions yet.")

    # EXPORT
    with tabs[5]:
        st.subheader("Export Results")
        if results:
            df=pd.DataFrame(results).T
            csv=df.to_csv().encode("utf-8")
            st.download_button("📥 Download CSV",csv,"results.csv")
        else: st.info("No data available.")

# ---------------------------
# ADMIN LOGIN
# ---------------------------
def admin_login():
    st.title("🔐 Admin Login")
    user=st.text_input("Username")
    pwd=st.text_input("Password",type="password")
    if st.button("Login"):
        if user=="admin" and pwd=="admin123":
            ss.logged_in=True
            st.rerun()
        else: st.error("Invalid credentials!")

# ---------------------------
# ROUTER
# ---------------------------
params=st.experimental_get_query_params()
quiz_id=params.get("quiz",[None])[0]
if quiz_id: student_quiz_page(quiz_id)
elif not ss.logged_in: admin_login()
else: admin_panel()
