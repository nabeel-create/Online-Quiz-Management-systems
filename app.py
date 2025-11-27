import streamlit as st
import sqlite3
import bcrypt
from datetime import datetime

# -----------------------
# Database setup (same as before)
# -----------------------
conn = sqlite3.connect("quiz.db", check_same_thread=False)
c = conn.cursor()
# tables creation code here (users, quizzes, assignments, results, uploads)
# ... same as previous full code ...

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
st.set_page_config(page_title="School System", layout="wide")
st.title("🏫 Online School Management System")

# -----------------------
# Authentication (same)
# -----------------------
# code for login here (same as previous full code)
# ...

# -----------------------
# Teacher Panel with Beautiful UI
# -----------------------
if st.session_state.logged_in and st.session_state.role == "teacher":
    st.header(f"Welcome, {st.session_state.username} (Teacher)")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📝 Add Quiz"):
            st.session_state.section = "add_quiz"
    with col2:
        if st.button("📄 Add Assignment"):
            st.session_state.section = "add_assignment"
    with col3:
        if st.button("📊 View Results"):
            st.session_state.section = "view_results"

    # Show section content dynamically
    section = st.session_state.get("section", None)
    if section == "add_quiz":
        st.subheader("Create New Quiz")
        quiz_name = st.text_input("Quiz Name", key="quiz_name")
        question = st.text_input("Question", key="question")
        options = st.text_area("Options (comma separated)")
        answer = st.text_input("Answer", key="answer")
        if st.button("Add Question"):
            c.execute("INSERT INTO quizzes (quiz_name, question, options, answer, teacher) VALUES (?, ?, ?, ?, ?)",
                      (quiz_name, question, options, answer, st.session_state.username))
            conn.commit()
            st.success(f"Question added to quiz '{quiz_name}'!")

    elif section == "add_assignment":
        st.subheader("Add Assignment")
        assign_name = st.text_input("Assignment Name", key="assign_name")
        assign_desc = st.text_area("Description", key="assign_desc")
        deadline = st.date_input("Deadline")
        if st.button("Add Assignment"):
            c.execute("INSERT INTO assignments (name, description, deadline, teacher) VALUES (?, ?, ?, ?)",
                      (assign_name, assign_desc, str(deadline), st.session_state.username))
            conn.commit()
            st.success(f"Assignment '{assign_name}' added!")

    elif section == "view_results":
        st.subheader("Student Results")
        c.execute("SELECT username, quiz_name, score FROM results")
        data = c.fetchall()
        if data:
            for u, q, s in data:
                st.write(f"- {u} | Quiz: {q} | Score: {s}")
        else:
            st.info("No results yet.")

# -----------------------
# Student Panel with Beautiful UI
# -----------------------
elif st.session_state.logged_in and st.session_state.role == "student":
    st.header(f"Welcome, {st.session_state.username} (Student)")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📝 Take Quiz"):
            st.session_state.section = "take_quiz"
    with col2:
        if st.button("📂 Upload Assignment"):
            st.session_state.section = "upload_assignment"
    with col3:
        if st.button("📊 View Scores"):
            st.session_state.section = "view_scores"

    section = st.session_state.get("section", None)

    if section == "take_quiz":
        st.subheader("Available Quizzes")
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
                    options_list = [o.strip() for o in opts.split(",")]
                    user_ans = st.radio("Choose answer:", options_list, key=f"{quiz_choice}_{idx}")
                    user_answers[q] = user_ans
                    if user_ans == ans:
                        user_score += 1
                if st.button("Submit Quiz"):
                    c.execute("INSERT INTO results (username, quiz_name, score, user_answers) VALUES (?, ?, ?, ?)",
                              (st.session_state.username, quiz_choice, user_score, str(user_answers)))
                    conn.commit()
                    st.success(f"You scored {user_score}/{len(questions)}")
        else:
            st.info("No quizzes available.")

    elif section == "upload_assignment":
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
            st.info("No assignments available.")

    elif section == "view_scores":
        st.subheader("Your Quiz Scores")
        c.execute("SELECT quiz_name, score FROM results WHERE username=?", (st.session_state.username,))
        scores = c.fetchall()
        if scores:
            for q, s in scores:
                st.write(f"- {q}: {s}")
        else:
            st.info("No scores yet.")
