import streamlit as st
import json, uuid, os, time
from datetime import datetime
import pandas as pd

# ---------------------------
# Ensure data folder exists
# ---------------------------
if not os.path.exists("data"):
    os.makedirs("data")

QUIZ_FILE = "data/quizzes.json"
RESULT_FILE = "data/results.json"

def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

quizzes = load_json(QUIZ_FILE)
results = load_json(RESULT_FILE)

# ---------------------------
# Streamlit Page Settings
# ---------------------------
st.set_page_config(page_title="Online Quiz System", layout="wide")

# ---------------------------
# CSS Styling
# ---------------------------
st.markdown("""
<style>
.quiz-card {
    padding: 20px;
    border-radius: 12px;
    background: #f8f9fa;
    border: 2px solid #eee;
    transition: 0.3s;
}
.quiz-card:hover {
    background: #f0f0f0;
    border-color: #999;
}
.button-style {
    background-color: #4CAF50;
    color: white;
    padding: 10px 25px;
    text-align: center;
    font-size: 16px;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# SESSION STATE
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None
if "start_time" not in st.session_state:
    st.session_state.start_time = None

# ---------------------------
# BASE URL (st.secrets)
# ---------------------------
def get_base_url():
    try:
        return st.secrets["APP_URL"]
    except:
        try:
            url = st.request.url
            return url.split("?")[0]
        except:
            return "http://localhost:8501"

BASE_URL = get_base_url()

# ---------------------------
# ADMIN LOGIN
# ---------------------------
def admin_login():
    st.title("🔐 Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state.logged_in = True
            st.success("Login Successful!")
            st.rerun()
        else:
            st.error("Invalid credentials!")

# ---------------------------
# ADMIN DASHBOARD
# ---------------------------
def admin_panel():
    st.title("👑 Admin Dashboard")
    tab1, tab2, tab3 = st.tabs(["➕ Create Quiz", "📄 Quiz List", "📊 Student Results"])

    # -----------------
    # Create Quiz
    # -----------------
    with tab1:
        st.subheader("Create a New Quiz")
        quiz_name = st.text_input("Quiz Name")
        time_limit = st.number_input("Time Limit (Minutes)", 1, 60, 5)
        if st.button("Create Quiz"):
            if not quiz_name:
                st.error("Enter quiz name!")
            else:
                quiz_id = str(uuid.uuid4())
                quizzes[quiz_id] = {"name": quiz_name, "time_limit": time_limit, "questions":[]}
                save_json(QUIZ_FILE, quizzes)
                quiz_link = f"{BASE_URL}?quiz={quiz_id}"
                st.success("✅ Quiz Created!")
                st.text_input("Share this link with students:", quiz_link)

        st.write("---")
        st.subheader("Add Questions to Quiz")
        if quizzes:
            selected = st.selectbox("Select Quiz", list(quizzes.keys()), format_func=lambda x: quizzes[x]["name"])
            q = st.text_input("Question")
            opts = st.text_input("Options (comma separated)")
            ans = st.text_input("Correct Answer")
            if st.button("Add Question"):
                if q and opts and ans:
                    quizzes[selected]["questions"].append({
                        "question": q,
                        "options": [o.strip() for o in opts.split(",")],
                        "answer": ans.strip()
                    })
                    save_json(QUIZ_FILE, quizzes)
                    st.success("✅ Question added!")
                else:
                    st.error("Fill all fields!")
        else:
            st.info("No quizzes yet. Create one!")

    # -----------------
    # Quiz List
    # -----------------
    with tab2:
        st.subheader("All Quizzes")
        for qid, qdata in quizzes.items():
            with st.container():
                st.markdown(f"<div class='quiz-card'>", unsafe_allow_html=True)
                st.write(f"### {qdata['name']}")
                st.write(f"Time Limit: **{qdata['time_limit']} min**")
                st.write(f"Questions: **{len(qdata['questions'])}**")
                quiz_link = f"{BASE_URL}?quiz={qid}"
                st.code(quiz_link)
                st.markdown("</div>", unsafe_allow_html=True)

    # -----------------
    # Student Results
    # -----------------
    with tab3:
        st.subheader("Student Submissions")
        if results:
            df = pd.DataFrame.from_dict(results, orient="index")
            st.dataframe(df)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", data=csv, file_name="quiz_results.csv")
        else:
            st.info("No submissions yet.")

# ---------------------------
# STUDENT QUIZ PAGE
# ---------------------------
def student_quiz_page(quiz_id):
    if quiz_id not in quizzes:
        st.error("Invalid Quiz!")
        return
    quiz = quizzes[quiz_id]
    st.title(f"📝 {quiz['name']}")
    st.info(f"Time Limit: {quiz['time_limit']} min")

    name = st.text_input("Your Name")
    regno = st.text_input("Registration Number")

    if st.button("Start Quiz"):
        if not name or not regno:
            st.error("Enter your details!")
            return
        st.session_state.current_quiz = quiz_id
        st.session_state.start_time = time.time()
        st.session_state.name = name
        st.session_state.regno = regno
        st.rerun()

    # If quiz started
    if st.session_state.current_quiz == quiz_id:
        start = st.session_state.start_time
        remaining = quiz["time_limit"]*60 - (time.time()-start)
        if remaining <= 0:
            st.error("⏳ Time Over!")
            return
        st.warning(f"⏰ Time Left: {int(remaining)} sec")

        answers = {}
        for i, q in enumerate(quiz["questions"]):
            st.write(f"### Q{i+1}: {q['question']}")
            answers[i] = st.radio("", q["options"], key=f"q{i}")

        if st.button("Submit Quiz"):
            score = sum(1 for i, q in enumerate(quiz["questions"]) if answers[i]==q["answer"])
            rid = str(uuid.uuid4())
            results[rid] = {
                "name": st.session_state.name,
                "regno": st.session_state.regno,
                "quiz_id": quiz_id,
                "score": score,
                "date": str(datetime.now())
            }
            save_json(RESULT_FILE, results)
            st.success(f"🎉 Quiz Submitted! Score: {score}/{len(quiz['questions'])}")
            st.balloons()

# ---------------------------
# ROUTER
# ---------------------------
params = st.experimental_get_query_params()
quiz_id = params.get("quiz", [None])[0]

if quiz_id:
    student_quiz_page(quiz_id)
elif not st.session_state.logged_in:
    admin_login()
else:
    admin_panel()
