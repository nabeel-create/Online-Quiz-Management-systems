import streamlit as st
import os, json, uuid, time, math, base64
import pandas as pd
import altair as alt
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from streamlit_autorefresh import st_autorefresh

# --------------------------------------------------
#  CREATE DATA FOLDERS
# --------------------------------------------------
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
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

quizzes = load_json(QUIZ_FILE, {})
results = load_json(RESULT_FILE, {})
users   = load_json(USER_FILE, {})

# --------------------------------------------------
# STREAMLIT PAGE SETUP
# --------------------------------------------------
st.set_page_config(page_title="AI Quiz System", layout="wide")

st.markdown("""
<style>
.quiz-card {
    padding: 15px;
    border-radius: 12px;
    background:#f8f9fa;
    margin-bottom:15px;
    border:2px solid #eee;
}
.quiz-card:hover { background:#f0f0f0; }
.dark .quiz-card { background:#2d2d2d; border-color:#555; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
ss = st.session_state
ss.setdefault("logged_in", False)
ss.setdefault("quiz_started", False)
ss.setdefault("question_index", 0)
ss.setdefault("answers", {})
ss.setdefault("start_time", None)

# --------------------------------------------------
# DARK MODE
# --------------------------------------------------
if "theme" not in ss:
    ss.theme = "light"

if st.button("Toggle Dark/Light Theme"):
    ss.theme = "dark" if ss.theme == "light" else "light"

if ss.theme == "dark":
    st.markdown("<body class='dark'>", unsafe_allow_html=True)

# --------------------------------------------------
# TIMER SVG
# --------------------------------------------------
def circular_timer(seconds_left, total_seconds):
    pct = seconds_left/total_seconds
    radius = 80
    color = "#4CAF50" if pct > 0.2 else "#FF0000"
    svg = f"""
    <svg width="200" height="200">
      <circle cx="100" cy="100" r="{radius}" fill="none" stroke="#eee" stroke-width="15"/>
      <circle cx="100" cy="100" r="{radius}" fill="none" stroke="{color}" stroke-width="15"
        stroke-dasharray="{2*math.pi*radius*pct}, {2*math.pi*radius}"/>
      <text x="100" y="110" text-anchor="middle" font-size="24" fill="black">{int(seconds_left)}s</text>
    </svg>
    """
    st.markdown(svg, unsafe_allow_html=True)

# --------------------------------------------------
# CERTIFICATE GENERATION (LOGO + PROFESSIONAL MINIMAL)
# --------------------------------------------------
def generate_certificate(name, quiz_name, score, total):
    cert_path = f"data/certificate_{uuid.uuid4()}.pdf"
    c = canvas.Canvas(cert_path, pagesize=letter)
    width, height = letter

    # BORDER
    c.setLineWidth(4)
    c.rect(20, 20, width - 40, height - 40)

    # LOGO IF EXISTS
    if os.path.exists(LOGO_FILE):
        logo = ImageReader(LOGO_FILE)
        c.drawImage(logo, width/2 - 60, height - 150, width=120, height=80, preserveAspectRatio=True)

    # HEADER
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width/2, height - 180, "Certificate of Achievement")

    # NAME
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width/2, height - 240, name)

    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2, height - 270, "has successfully completed")

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height - 300, quiz_name)

    # SCORE
    c.setFont("Helvetica", 14)
    c.drawCentredString(width/2, height - 340, f"Score: {score}/{total}")

    # DATE
    c.drawCentredString(width/2, height - 370, datetime.now().strftime("%d %B %Y"))

    c.showPage()
    c.save()
    return cert_path

# --------------------------------------------------
# STUDENT QUIZ PAGE
# --------------------------------------------------
def student_quiz_page(quiz_id):
    if quiz_id not in quizzes:
        st.error("Invalid Quiz")
        return

    quiz = quizzes[quiz_id]

    st.title(f"📝 {quiz['name']}")
    st.info(f"Time Limit: {quiz['time_limit']} min")

    if not ss.quiz_started:
        ss.name = st.text_input("Your Name")
        ss.regno = st.text_input("Registration Number")
        if st.button("Start Quiz"):
            if not ss.name or not ss.regno:
                st.error("Enter your details")
                return

            ss.quiz_started = True
            ss.start_time = time.time()
            ss.question_index = 0
            ss.answers = {}

            # SHUFFLE QUESTIONS
            quiz["questions"] = quiz["questions"].copy()
            import random
            random.shuffle(quiz["questions"])

            st.rerun()

    else:
        start = ss.start_time
        total_sec = quiz["time_limit"] * 60
        remaining = total_sec - (time.time() - start)

        if remaining <= 0:
            ss.quiz_started = False
            st.error("⏳ Time Over! Auto-submitted.")
            st.rerun()

        circular_timer(remaining, total_sec)

        idx = ss.question_index
        q = quiz["questions"][idx]

        st.write(f"### Q{idx+1}/{len(quiz['questions'])}")
        st.write(q["question"])

        qtype = q.get("type", "mcq")

        if qtype == "mcq":
            import random
            opts = q["options"].copy()
            random.shuffle(opts)
            ans = st.radio("Select one:", opts, key=f"q{idx}")

        elif qtype == "truefalse":
            ans = st.radio("Select:", ["True", "False"], key=f"q{idx}")

        elif qtype == "short":
            ans = st.text_input("Answer:", key=f"q{idx}")

        elif qtype == "fill":
            ans = st.text_input("Fill in the blank:", key=f"q{idx}")

        ss.answers[idx] = ans

        col1, col2 = st.columns(2)

        with col1:
            if idx > 0 and st.button("⬅ Previous"):
                ss.question_index -= 1
                st.rerun()

        with col2:
            if idx < len(quiz["questions"])-1 and st.button("Next ➡"):
                ss.question_index += 1
                st.rerun()
            elif idx == len(quiz["questions"])-1 and st.button("Submit Quiz"):
                score = 0
                for i, ques in enumerate(quiz["questions"]):
                    if str(ss.answers.get(i, "")).strip().lower() == str(ques["answer"]).strip().lower():
                        score += 1

                rid = str(uuid.uuid4())
                results[rid] = {
                    "name": ss.name,
                    "regno": ss.regno,
                    "quiz_id": quiz_id,
                    "score": score,
                    "total": len(quiz["questions"]),
                    "date": str(datetime.now())
                }
                save_json(RESULT_FILE, results)

                st.success(f"🎉 Quiz Submitted! Score: {score}/{len(quiz['questions'])}")

                # Certificate
                cert_path = generate_certificate(ss.name, quiz["name"], score, len(quiz["questions"]))
                with open(cert_path, "rb") as f:
                    st.download_button("🎖 Download Certificate", data=f, file_name="certificate.pdf")

                st.balloons()
                ss.quiz_started = False

# --------------------------------------------------
# ADMIN PANEL
# --------------------------------------------------
def admin_panel():
    st.title("👑 Admin Dashboard")

    tabs = st.tabs(["➕ Create Quiz", "📄 Quiz List", "📊 Results", "🎓 Question Bank", "🏅 Leaderboard", "📤 Export"])

    # --------------------------------------------------
    # CREATE QUIZ
    # --------------------------------------------------
    with tabs[0]:
        st.subheader("Create Quiz")
        name = st.text_input("Quiz Name")
        time_limit = st.number_input("Time Limit (min)", 1, 60, 5)

        if st.button("Create Quiz"):
            qid = str(uuid.uuid4())
            quizzes[qid] = {"name": name, "time_limit": time_limit, "questions": []}
            save_json(QUIZ_FILE, quizzes)
            st.success("Quiz Created!")

        st.write("---")
        st.subheader("Add Questions")
        if quizzes:
            qid = st.selectbox("Select Quiz", quizzes.keys(), format_func=lambda x: quizzes[x]["name"])
            text = st.text_input("Question")
            qtype = st.selectbox("Question Type", ["mcq", "truefalse", "short", "fill"])

            if qtype == "mcq":
                options = st.text_input("Options (comma)")
                answer = st.text_input("Correct Answer")
            elif qtype == "truefalse":
                options = ["True", "False"]
                answer = st.selectbox("Correct Answer", options)
            else:
                options = []
                answer = st.text_input("Correct Answer")

            if st.button("Add Question"):
                quizzes[qid]["questions"].append({
                    "question": text,
                    "type": qtype,
                    "options": options if isinstance(options, list) else [o.strip() for o in options.split(",")],
                    "answer": answer
                })
                save_json(QUIZ_FILE, quizzes)
                st.success("Question Added!")

        st.write("---")
        st.subheader("Upload Certificate Logo")
        logo = st.file_uploader("Upload PNG Logo", type=["png"])
        if logo:
            with open(LOGO_FILE, "wb") as f:
                f.write(logo.read())
            st.success("Logo Uploaded!")

    # --------------------------------------------------
    # QUIZ LIST
    # --------------------------------------------------
    with tabs[1]:
        st.subheader("All Quizzes")
        query = st.text_input("Search Quiz")
        for qid, q in quizzes.items():
            if query.lower() in q["name"].lower():
                st.markdown(f"<div class='quiz-card'>", unsafe_allow_html=True)
                st.write(f"### {q['name']}")
                st.write(f"Time: {q['time_limit']} min")
                st.write(f"Questions: {len(q['questions'])}")
                st.code(f"{st.experimental_get_query_params()}?quiz={qid}")
                if st.button("Delete", key=qid):
                    del quizzes[qid]
                    save_json(QUIZ_FILE, quizzes)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # RESULTS
    # --------------------------------------------------
    with tabs[2]:
        st.subheader("Live Results")
        st_autorefresh(interval=4000)

        if results:
            df = pd.DataFrame(results).T
            st.dataframe(df)
            st.metric("Total Submissions", len(df))
        else:
            st.info("No results yet.")

    # --------------------------------------------------
    # QUESTION BANK
    # --------------------------------------------------
    with tabs[3]:
        st.subheader("Question Bank")
        st.info("All added questions can be reused here.")

        bank = []
        for qid, qz in quizzes.items():
            for q in qz["questions"]:
                bank.append(q)

        if bank:
            st.dataframe(pd.DataFrame(bank))
        else:
            st.info("No questions in bank.")

    # --------------------------------------------------
    # LEADERBOARD
    # --------------------------------------------------
    with tabs[4]:
        st.subheader("Leaderboard")
        if results:
            df = pd.DataFrame(results).T
            df.sort_values("score", ascending=False, inplace=True)
            st.dataframe(df[["name", "score", "total", "date"]])
        else:
            st.info("No submissions yet.")

    # --------------------------------------------------
    # EXPORT
    # --------------------------------------------------
    with tabs[5]:
        st.subheader("Export Results")

        if results:
            df = pd.DataFrame(results).T

            csv = df.to_csv().encode("utf-8")
            st.download_button("📥 Download CSV", csv, "results.csv")

            # Simple PDF export
            pdf_path = "data/results_export.pdf"
            c = canvas.Canvas(pdf_path, pagesize=letter)
            c.drawString(50, 770, "Quiz Results Export")
            n = 720
            for i, row in df.iterrows():
                c.drawString(50, n, f"{row['name']} - {row['score']}/{row['total']} ({row['date']})")
                n -= 20
            c.save()

            with open(pdf_path, "rb") as f:
                st.download_button("📄 Download PDF", f, "results.pdf")
        else:
            st.info("No data available.")

# --------------------------------------------------
# LOGIN PAGE
# --------------------------------------------------
def admin_login():
    st.title("🔐 Admin Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == "admin" and pwd == "admin123":
            ss.logged_in = True
            st.rerun()
        else:
            st.error("Invalid Login")

# --------------------------------------------------
# ROUTER
# --------------------------------------------------
params = st.experimental_get_query_params()
quiz_id = params.get("quiz", [None])[0]

if quiz_id:
    student_quiz_page(quiz_id)
elif not ss.logged_in:
    admin_login()
else:
    admin_panel()
