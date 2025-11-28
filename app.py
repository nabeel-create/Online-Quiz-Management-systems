import streamlit as st
import pandas as pd
import uuid
from datetime import datetime

# --------------------------
# PAGE CONFIG
# --------------------------
st.set_page_config(page_title="Online Quiz System", layout="wide")

# --------------------------
# GLOBAL STORAGE (In-memory)
# --------------------------
if "quizzes" not in st.session_state:
    st.session_state.quizzes = {}

if "submissions" not in st.session_state:
    st.session_state.submissions = []

# --------------------------
# GET BASE URL SAFE
# --------------------------
def get_base_url():
    try:
        url = st.request.url  # Works on Streamlit Cloud
        base = url.split("?")[0]
        return base
    except:
        return "http://localhost:8501"

BASE_URL = get_base_url()

# --------------------------
# ADMIN LOGIN
# --------------------------
def admin_login():
    st.title("🔐 Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state["admin"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect username or password")

# --------------------------
# ADMIN PANEL
# --------------------------
def admin_panel():
    st.title("🛠 Admin Panel")

    # Refresh button
    if st.button("🔄 Refresh Page"):
        st.rerun()

    st.subheader("➕ Create New Quiz")

    question = st.text_area("Enter Question")
    option1 = st.text_input("Option A")
    option2 = st.text_input("Option B")
    option3 = st.text_input("Option C")
    option4 = st.text_input("Option D")
    correct = st.selectbox("Correct Option", ["A", "B", "C", "D"])
    timer = st.number_input("Timer (Seconds)", min_value=10, max_value=600, value=60)

    if st.button("Create Quiz"):
        qid = str(uuid.uuid4())[:8]
        st.session_state.quizzes[qid] = {
            "question": question,
            "options": [option1, option2, option3, option4],
            "correct": correct,
            "timer": timer
        }

        quiz_link = f"{BASE_URL}?quiz={qid}"

        st.success("✅ Quiz Created Successfully!")

        # Auto-write quiz link
        st.text_input("Quiz Link", quiz_link)

    # -------------------------
    st.subheader("📋 Students Submitted")

    df = pd.DataFrame(st.session_state.submissions,
                      columns=["Name", "Quiz ID", "Answer", "Correct?", "Time"])

    st.dataframe(df, use_container_width=True)


# --------------------------
# QUIZ PAGE FOR STUDENTS
# --------------------------
def student_quiz(qid):
    quiz = st.session_state.quizzes.get(qid)

    if not quiz:
        st.error("Quiz not found.")
        return

    st.title("🎓 Quiz Time!")

    st.write(quiz["question"])

    answer = st.radio("Choose your answer:", ["A", "B", "C", "D"])

    if st.button("Submit Answer"):
        correct = "Yes" if answer == quiz["correct"] else "No"

        st.session_state.submissions.append([
            "Student",  # you can add login system later
            qid,
            answer,
            correct,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ])

        if correct == "Yes":
            st.success("🎉 Correct Answer!")
        else:
            st.error("❌ Wrong Answer!")

# --------------------------
# ROUTING SYSTEM
# --------------------------
params = st.experimental_get_query_params()
quiz_id = params.get("quiz", [None])[0]

if quiz_id:
    student_quiz(quiz_id)
else:
    if "admin" not in st.session_state:
        admin_login()
    else:
        admin_panel()
