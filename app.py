import streamlit as st
import sqlite3
import bcrypt
import pandas as pd

# -----------------------
# Database setup
# -----------------------
conn = sqlite3.connect("quiz.db", check_same_thread=False)
c = conn.cursor()

# Create tables if not exist
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
    answer TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    quiz_name TEXT,
    score INTEGER,
    user_answers TEXT
)''')
conn.commit()

# -----------------------
# Utility functions
# -----------------------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def add_user(username, password, role):
    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
              (username, hash_password(password), role))
    conn.commit()

def get_user(username):
    c.execute("SELECT username, password, role FROM users WHERE username=?", (username,))
    return c.fetchone()

def add_quiz(quiz_name, question, options, answer):
    c.execute("INSERT INTO quizzes (quiz_name, question, options, answer) VALUES (?, ?, ?, ?)",
              (quiz_name, question, options, answer))
    conn.commit()

def get_quizzes():
    c.execute("SELECT DISTINCT quiz_name FROM quizzes")
    return [q[0] for q in c.fetchall()]

def get_quiz_questions(quiz_name):
    c.execute("SELECT question, options, answer FROM quizzes WHERE quiz_name=?", (quiz_name,))
    return c.fetchall()

def save_result(username, quiz_name, score, user_answers):
    c.execute("INSERT INTO results (username, quiz_name, score, user_answers) VALUES (?, ?, ?, ?)",
              (username, quiz_name, score, str(user_answers)))
    conn.commit()

def get_results():
    c.execute("SELECT username, quiz_name, score, user_answers FROM results")
    return c.fetchall()

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="Quiz System", page_icon="📝", layout="centered")
st.title("📝 Online Quiz Management System")

# -----------------------
# Sidebar Authentication
# -----------------------
st.sidebar.title("Login / SignUp")
auth_choice = st.sidebar.radio("Action", ["Login", "SignUp"])

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None

# -----------------------
# SignUp
# -----------------------
if auth_choice == "SignUp":
    st.subheader("Create New Account")
    new_username = st.text_input("Username", key="signup_username")
    new_password = st.text_input("Password", type="password", key="signup_pass")
    role = st.selectbox("Role", ["user", "admin"], key="signup_role")

    if st.button("Sign Up"):
        if get_user(new_username):
            st.error("Username already exists!")
        elif not new_username or not new_password:
            st.error("Enter valid username and password")
        else:
            add_user(new_username, new_password, role)
            st.success("Account created! Please login.")

# -----------------------
# Login
# -----------------------
elif auth_choice == "Login":
    st.subheader("Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login"):
        user = get_user(username)
        if user and check_password(password, user[1]):
            st.session_state.logged_in = True
            st.session_state.username = user[0]
            st.session_state.role = user[2]
            st.success(f"Logged in as {username}")
        else:
            st.error("Invalid Username or Password")

# -----------------------
# Main Panel
# -----------------------
if st.session_state.logged_in:
    st.sidebar.success(f"Logged in as {st.session_state.username} ({st.session_state.role})")
    if st.session_state.role == "admin":
        st.header("Admin Panel 🛠️")
        st.subheader("Add New Question")
        quiz_name = st.text_input("Quiz Name", key="admin_quiz_name")
        question_text = st.text_input("Question", key="admin_question_text")
        options_text = st.text_area("Options (comma separated)", key="admin_options_text")
        answer_text = st.text_input("Answer", key="admin_answer_text")

        if st.button("Add Question", key="add_question"):
            if not all([quiz_name, question_text, options_text, answer_text]):
                st.error("Please fill all fields")
            else:
                add_quiz(quiz_name, question_text, options_text, answer_text)
                st.success("Question added successfully!")

        st.subheader("All Quizzes")
        quizzes_list = get_quizzes()
        for qname in quizzes_list:
            st.write(f"**{qname}**")
            for q, opts, ans in get_quiz_questions(qname):
                st.write(f"- {q} | Answer: {ans}")

        st.subheader("All Results")
        res = get_results()
        for u, qn, score, ua in res:
            st.write(f"- {u} | {qn} | Score: {score} | Answers: {ua}")

    else:
        st.header("User Panel 🎯")
        quizzes_list = get_quizzes()
        if not quizzes_list:
            st.info("No quizzes available.")
        else:
            quiz_choice = st.selectbox("Select Quiz", quizzes_list)
            if quiz_choice:
                questions = get_quiz_questions(quiz_choice)
                user_score = 0
                user_answers = {}
                for idx, (q, opts, ans) in enumerate(questions):
                    st.write(f"Q{idx+1}: {q}")
                    options = [o.strip() for o in opts.split(",")]
                    user_ans = st.radio("Choose an answer:", options, key=f"{quiz_choice}_{idx}")
                    user_answers[q] = user_ans
                    if user_ans == ans:
                        user_score += 1

                if st.button("Submit Quiz"):
                    save_result(st.session_state.username, quiz_choice, user_score, user_answers)
                    st.success(f"You scored {user_score}/{len(questions)}")
