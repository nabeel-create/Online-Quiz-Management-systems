import streamlit as st
import sqlite3
import bcrypt
from datetime import datetime

# -----------------------
# Database setup
# -----------------------
conn = sqlite3.connect("quiz.db", check_same_thread=False)
c = conn.cursor()

# Tables
c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)''')

c.execute('''CREATE TABLE IF NOT EXISTS quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_name TEXT,
    question TEXT,
    options TEXT,
    answer TEXT,
    teacher TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    deadline TEXT,
    teacher TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    quiz_name TEXT,
    score INTEGER,
    user_answers TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    assignment_name TEXT,
    file_name TEXT
)''')

conn.commit()

# -----------------------
# Utility functions
# -----------------------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def get_user(username):
    c.execute("SELECT username, password, role FROM users WHERE username=?", (username,))
    return c.fetchone()

def add_user(username, password, role):
    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
              (username, hash_password(password), role))
    conn.commit()

# -----------------------
# Session state init
# -----------------------
for key in ["logged_in", "username", "role", "section"]:
    if key not in st.session_state:
        st.session_state[key] = None

# -----------------------
# Page setup
# -----------------------
st.set_page_config(page_title="Online School System", layout="wide")
st.title("🏫 Online School System")

# -----------------------
# LOGIN PANEL
# -----------------------
if not st.session_state.logged_in:
    st.subheader("Login")
    role = st.selectbox("Login as", ["Admin", "Teacher", "Student"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = get_user(username)
        if user and check_password(password, user[1]) and user[2] == role.lower():
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role.lower()
            st.success(f"Logged in as {username} ({role})")
        else:
            st.error("Invalid credentials or role")

# -----------------------
# CARD FUNCTION
# -----------------------
def create_card(title, emoji, key):
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button(emoji + " " + title, key=key):
            st.session_state.section = key

# -----------------------
# DASHBOARD AFTER LOGIN
# -----------------------
if st.session_state.logged_in:
    st.subheader(f"Welcome, {st.session_state.username} ({st.session_state.role.capitalize()})")

    if st.session_state.role == "admin":
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("👩‍🏫 Register Teacher", key="reg_teacher"):
                st.session_state.section = "reg_teacher"
        with col2:
            if st.button("👨‍🎓 Register Student", key="reg_student"):
                st.session_state.section = "reg_student"
        with col3:
            if st.button("📄 View Users", key="view_users"):
                st.session_state.section = "view_users"

        # Sections
        if st.session_state.section == "reg_teacher":
            st.subheader("Register Teacher")
            t_user = st.text_input("Username", key="t_user")
            t_pass = st.text_input("Password", type="password", key="t_pass")
            if st.button("Register Teacher"):
                if get_user(t_user):
                    st.error("Username already exists!")
                else:
                    add_user(t_user, t_pass, "teacher")
                    st.success(f"Teacher '{t_user}' registered!")

        elif st.session_state.section == "reg_student":
            st.subheader("Register Student")
            s_user = st.text_input("Username", key="s_user")
            s_pass = st.text_input("Password", type="password", key="s_pass")
            if st.button("Register Student"):
                if get_user(s_user):
                    st.error("Username already exists!")
                else:
                    add_user(s_user, s_pass, "student")
                    st.success(f"Student '{s_user}' registered!")

        elif st.session_state.section == "view_users":
            st.subheader("All Users")
            c.execute("SELECT username, role FROM users")
            users = c.fetchall()
            for u, r in users:
                st.write(f"- {u} ({r})")

    elif st.session_state.role == "teacher":
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📝 Add Quiz", key="add_quiz"):
                st.session_state.section = "add_quiz"
        with col2:
            if st.button("📄 Add Assignment", key="add_assign"):
                st.session_state.section = "add_assignment"
        with col3:
            if st.button("📊 View Results", key="view_results"):
                st.session_state.section = "view_results"

        # Sections
        if st.session_state.section == "add_quiz":
            st.subheader("Add Quiz")
            quiz_name = st.text_input("Quiz Name", key="quiz_name")
            question = st.text_input("Question", key="question")
            options = st.text_area("Options (comma separated)")
            answer = st.text_input("Answer", key="answer")
            if st.button("Add Question"):
                c.execute("INSERT INTO quizzes (quiz_name, question, options, answer, teacher) VALUES (?, ?, ?, ?, ?)",
                          (quiz_name, question, options, answer, st.session_state.username))
                conn.commit()
                st.success(f"Question added to quiz '{quiz_name}'!")

        elif st.session_state.section == "add_assignment":
            st.subheader("Add Assignment")
            assign_name = st.text_input("Assignment Name", key="assign_name")
            assign_desc = st.text_area("Description", key="assign_desc")
            deadline = st.date_input("Deadline")
            if st.button("Add Assignment"):
                c.execute("INSERT INTO assignments (name, description, deadline, teacher) VALUES (?, ?, ?, ?)",
                          (assign_name, assign_desc, str(deadline), st.session_state.username))
                conn.commit()
                st.success(f"Assignment '{assign_name}' added!")

        elif st.session_state.section == "view_results":
            st.subheader("Student Results")
            c.execute("SELECT username, quiz_name, score FROM results")
            data = c.fetchall()
            if data:
                for u, q, s in data:
                    st.write(f"- {u} | Quiz: {q} | Score: {s}")
            else:
                st.info("No results yet.")

    elif st.session_state.role == "student":
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📝 Take Quiz", key="take_quiz"):
                st.session_state.section = "take_quiz"
        with col2:
            if st.button("📂 Upload Assignment", key="upload_assign"):
                st.session_state.section = "upload_assignment"
        with col3:
            if st.button("📊 View Scores", key="view_scores"):
                st.session_state.section = "view_scores"

        # Sections
        if st.session_state.section == "take_quiz":
            st.subheader("Take Quiz")
            c.execute("SELECT DISTINCT quiz_name FROM quizzes")
            quizzes = [q[0] for q in c.fetchall()]
            if quizzes:
                quiz_choice = st.selectbox("Select Quiz", quizzes)
                if quiz_choice:
                    c.execute("SELECT question, options, answer FROM quizzes WHERE quiz_name=?", (quiz_choice,))
                    questions = c.fetchall()
                    user_score = 0
                    user_answers = {}
                    for idx, (q, opts, ans) in enumerate(questions):
                        st.write(f"Q{idx+1}: {q}")
                        opts_list = [o.strip() for o in opts.split(",")]
                        user_ans = st.radio("Choose answer:", opts_list, key=f"{quiz_choice}_{idx}")
                        user_answers[q] = user_ans
                        if user_ans == ans:
                            user_score += 1
                    if st.button("Submit Quiz"):
                        c.execute("INSERT INTO results (username, quiz_name, score, user_answers) VALUES (?, ?, ?, ?)",
                                  (st.session_state.username, quiz_choice, user_score, str(user_answers)))
                        conn.commit()
                        st.success(f"You scored {user_score}/{len(questions)}")
            else:
                st.info("No quizzes available")

        elif st.session_state.section == "upload_assignment":
            st.subheader("Upload Assignment")
            c.execute("SELECT name FROM assignments")
            assignments = [a[0] for a in c.fetchall()]
            if assignments:
                assign_choice = st.selectbox("Select Assignment", assignments)
                uploaded_file = st.file_uploader("Choose file")
                if st.button("Submit Assignment"):
                    if uploaded_file:
                        file_path = f"data/{st.session_state.username}_{assign_choice}_{uploaded_file.name}"
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        c.execute("INSERT INTO uploads (username, assignment_name, file_name) VALUES (?, ?, ?)",
                                  (st.session_state.username, assign_choice, uploaded_file.name))
                        conn.commit()
                        st.success("Assignment uploaded successfully!")
            else:
                st.info("No assignments available")

        elif st.session_state.section == "view_scores":
            st.subheader("Your Quiz Scores")
            c.execute("SELECT quiz_name, score FROM results WHERE username=?", (st.session_state.username,))
            scores = c.fetchall()
            if scores:
                for q, s in scores:
                    st.write(f"- {q}: {s}")
            else:
                st.info("No scores yet.")
