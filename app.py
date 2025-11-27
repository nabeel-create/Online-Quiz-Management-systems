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
if "section" not in st.session_state:
    st.session_state.section = None

# -----------------------
# Page setup
# -----------------------
st.set_page_config(page_title="School System", layout="wide")
st.title("🏫 Online School System")

# -----------------------
# Login (same as before)
# -----------------------
# code for login here (admin/teacher/student)

# -----------------------
# Function to render clickable cards
# -----------------------
def card(title, emoji, key):
    """Render a clickable card with title and emoji."""
    card_html = f"""
    <div style="
        padding: 20px;
        text-align: center;
        border-radius: 15px;
        background-color:#f0f4f8;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        transition: 0.3s;
        cursor: pointer;
        margin-bottom: 20px;
    "
    onmouseover="this.style.transform='scale(1.05)';"
    onmouseout="this.style.transform='scale(1)';">
        <h2 style="font-size: 30px;">{emoji}</h2>
        <h3>{title}</h3>
    </div>
    """
    if st.button("", key=key):
        st.session_state.section = key
    st.markdown(card_html, unsafe_allow_html=True)

# -----------------------
# Teacher Dashboard with Cards
# -----------------------
if st.session_state.logged_in and st.session_state.role == "teacher":
    st.header(f"Welcome, {st.session_state.username} (Teacher)")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📝 Add Quiz", key="add_quiz_btn"):
            st.session_state.section = "add_quiz"
    with col2:
        if st.button("📄 Add Assignment", key="add_assign_btn"):
            st.session_state.section = "add_assignment"
    with col3:
        if st.button("📊 View Results", key="view_results_btn"):
            st.session_state.section = "view_results"

    # Render section dynamically
    if st.session_state.section == "add_quiz":
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
