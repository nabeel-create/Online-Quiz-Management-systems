import streamlit as st
import os
import json
from datetime import datetime

# -----------------------
# File paths
# -----------------------
os.makedirs("data", exist_ok=True)
USERS_FILE = "data/users.json"
QUIZZES_FILE = "data/quizzes.json"
ASSIGNMENTS_FILE = "data/assignments.json"
RESULTS_FILE = "data/results.json"
UPLOADS_DIR = "data/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Initialize files
for file in [USERS_FILE, QUIZZES_FILE, ASSIGNMENTS_FILE, RESULTS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

# -----------------------
# Utility functions
# -----------------------
def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# -----------------------
# Session state
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

# -----------------------
# Page setup
# -----------------------
st.set_page_config(page_title="Online School System", layout="centered")
st.title("🏫 Online School Management System")

# -----------------------
# Authentication
# -----------------------
if not st.session_state.logged_in:
    st.sidebar.subheader("Login")
    role = st.sidebar.selectbox("Login as", ["Admin", "Teacher", "Student"])
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Login"):
        users = load_json(USERS_FILE)
        if username in users and users[username]["password"] == password and users[username]["role"] == role.lower():
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role.lower()
            st.success(f"Logged in as {username} ({role})")
        else:
            st.error("Invalid credentials or role")

# -----------------------
# Admin Panel
# -----------------------
if st.session_state.logged_in and st.session_state.role == "admin":
    st.header("Admin Panel 🛠️")
    st.subheader("Register Users")

    reg_role = st.selectbox("Role to register", ["Teacher", "Student"])
    reg_username = st.text_input("Username", key="reg_username")
    reg_password = st.text_input("Password", type="password", key="reg_password")
    if st.button("Register User"):
        if not all([reg_username, reg_password]):
            st.error("Fill all fields")
        else:
            users = load_json(USERS_FILE)
            if reg_username in users:
                st.error("Username already exists!")
            else:
                users[reg_username] = {"password": reg_password, "role": reg_role.lower()}
                save_json(USERS_FILE, users)
                st.success(f"{reg_role} '{reg_username}' registered successfully!")

    st.subheader("All Users")
    users = load_json(USERS_FILE)
    for uname, info in users.items():
        st.write(f"- {uname} | Role: {info['role'].capitalize()}")

# -----------------------
# Teacher Panel
# -----------------------
elif st.session_state.logged_in and st.session_state.role == "teacher":
    st.header("Teacher Panel 📚")
    tab = st.radio("Select Section", ["Add Quiz", "Add Assignment", "View Student Scores"])

    # Add Quiz
    if tab == "Add Quiz":
        st.subheader("Create Quiz")
        quiz_name = st.text_input("Quiz Name", key="quiz_name")
        question = st.text_input("Question", key="question")
        options = st.text_area("Options (comma separated)")
        answer = st.text_input("Answer", key="answer")

        if st.button("Add Question"):
            if not all([quiz_name, question, options, answer]):
                st.error("Fill all fields")
            else:
                quizzes = load_json(QUIZZES_FILE)
                if quiz_name not in quizzes:
                    quizzes[quiz_name] = []
                quizzes[quiz_name].append({
                    "question": question,
                    "options": [opt.strip() for opt in options.split(",")],
                    "answer": answer.strip()
                })
                save_json(QUIZZES_FILE, quizzes)
                st.success(f"Question added to quiz '{quiz_name}'!")

    # Add Assignment
    elif tab == "Add Assignment":
        st.subheader("Create Assignment")
        assign_name = st.text_input("Assignment Name")
        assign_desc = st.text_area("Description")
        deadline = st.date_input("Deadline")
        if st.button("Add Assignment"):
            if not all([assign_name, assign_desc]):
                st.error("Fill all fields")
            else:
                assignments = load_json(ASSIGNMENTS_FILE)
                assignments[assign_name] = {"description": assign_desc, "deadline": str(deadline), "teacher": st.session_state.username}
                save_json(ASSIGNMENTS_FILE, assignments)
                st.success(f"Assignment '{assign_name}' created!")

    # View Scores
    elif tab == "View Student Scores":
        st.subheader("Student Results")
        results = load_json(RESULTS_FILE)
        if results:
            for student, res in results.items():
                st.write(f"**{student}**")
                for k, v in res.items():
                    st.write(f"- {k}: {v}")
        else:
            st.info("No student results yet.")

# -----------------------
# Student Panel
# -----------------------
elif st.session_state.logged_in and st.session_state.role == "student":
    st.header("Student Panel 🎓")
    tab = st.radio("Select Section", ["Take Quiz", "Upload Assignment", "View Scores"])

    # Take Quiz
    if tab == "Take Quiz":
        quizzes = load_json(QUIZZES_FILE)
        if not quizzes:
            st.info("No quizzes available")
        else:
            quiz_choice = st.selectbox("Select Quiz", list(quizzes.keys()))
            if quiz_choice:
                questions = quizzes[quiz_choice]
                user_score = 0
                user_answers = {}
                for idx, q in enumerate(questions):
                    st.write(f"Q{idx+1}: {q['question']}")
                    ans = st.radio("Choose an answer:", q["options"], key=f"{quiz_choice}_{idx}")
                    user_answers[q['question']] = ans
                    if ans == q['answer']:
                        user_score += 1
                if st.button("Submit Quiz"):
                    results = load_json(RESULTS_FILE)
                    if st.session_state.username not in results:
                        results[st.session_state.username] = {}
                    results[st.session_state.username][quiz_choice] = user_score
                    save_json(RESULTS_FILE, results)
                    st.success(f"You scored {user_score}/{len(questions)}")

    # Upload Assignment
    elif tab == "Upload Assignment":
        assignments = load_json(ASSIGNMENTS_FILE)
        if not assignments:
            st.info("No assignments available")
        else:
            assign_choice = st.selectbox("Select Assignment", list(assignments.keys()))
            uploaded_file = st.file_uploader("Upload File")
            if st.button("Submit Assignment"):
                if uploaded_file is not None:
                    file_path = os.path.join(UPLOADS_DIR, f"{st.session_state.username}_{assign_choice}_{uploaded_file.name}")
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success("Assignment uploaded successfully!")

    # View Scores
    elif tab == "View Scores":
        results = load_json(RESULTS_FILE)
        if st.session_state.username in results:
            st.subheader("Your Quiz Scores")
            for quiz, score in results[st.session_state.username].items():
                st.write(f"- {quiz}: {score}")
        else:
            st.info("No quiz results yet.")
