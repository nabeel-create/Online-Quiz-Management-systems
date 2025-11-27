import streamlit as st
import json
import os

# -----------------------
# File paths
# -----------------------
USERS_FILE = "data/users.json"
QUIZZES_FILE = "data/quizzes.json"

os.makedirs("data", exist_ok=True)

# Initialize files if not exist
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({"admin": {"password": "admin123"}}, f)  # default admin

if not os.path.exists(QUIZZES_FILE):
    with open(QUIZZES_FILE, "w") as f:
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
# Streamlit session state
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# -----------------------
# Admin Login
# -----------------------
st.title("📝 Quiz Management System")

if not st.session_state.logged_in:
    st.subheader("Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        users = load_json(USERS_FILE)
        if username in users and password == users[username]["password"]:
            st.session_state.logged_in = True
            st.success(f"Welcome, {username}")
        else:
            st.error("Invalid credentials")

# -----------------------
# Admin Panel
# -----------------------
if st.session_state.logged_in:
    st.header("Admin Panel 🛠️")
    
    # Create new quiz
    st.subheader("Create Quiz")
    quiz_name = st.text_input("Quiz Name")
    question = st.text_input("Question")
    options = st.text_area("Options (comma separated)")
    answer = st.text_input("Answer")
    
    if st.button("Add Question"):
        if not all([quiz_name, question, options, answer]):
            st.error("Fill all fields!")
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

    # Display quizzes as clickable links
    st.subheader("Available Quizzes")
    quizzes = load_json(QUIZZES_FILE)
    if quizzes:
        for qname in quizzes:
            if st.button(f"Take Quiz: {qname}", key=qname):
                st.session_state.current_quiz = qname
    else:
        st.info("No quizzes available yet.")

# -----------------------
# Take Quiz Panel
# -----------------------
if "current_quiz" in st.session_state:
    st.header(f"Quiz: {st.session_state.current_quiz}")
    quizzes = load_json(QUIZZES_FILE)
    quiz_questions = quizzes[st.session_state.current_quiz]
    
    user_score = 0
    user_answers = {}
    for idx, q in enumerate(quiz_questions):
        st.write(f"Q{idx+1}: {q['question']}")
        ans = st.radio("Choose answer:", q["options"], key=f"{st.session_state.current_quiz}_{idx}")
        user_answers[q['question']] = ans
        if ans == q['answer']:
            user_score += 1
    
    if st.button("Submit Quiz"):
        st.success(f"You scored {user_score}/{len(quiz_questions)}")
        del st.session_state.current_quiz
