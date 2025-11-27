import streamlit as st
import json
import os

# -----------------------
# File paths
# -----------------------
QUIZZES_FILE = "data/quizzes.json"
RESULTS_FILE = "data/results.json"

os.makedirs("data", exist_ok=True)

if not os.path.exists(QUIZZES_FILE):
    with open(QUIZZES_FILE, "w") as f:
        json.dump({
            "Sample Quiz": [
                {"question": "Capital of Pakistan?", "options": ["Islamabad", "Karachi", "Lahore", "Peshawar"], "answer": "Islamabad"},
                {"question": "2 + 2 = ?", "options": ["3", "4", "5", "6"], "answer": "4"}
            ]
        }, f)

if not os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, "w") as f:
        json.dump({}, f)

# -----------------------
# Load / Save JSON
# -----------------------
def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# -----------------------
# Streamlit Page Setup
# -----------------------
st.set_page_config(page_title="Student Quiz Portal", page_icon="📝", layout="centered")
st.markdown("<h1 style='text-align:center;color:#4B0082;'>🎓 Student Quiz Portal</h1>", unsafe_allow_html=True)
st.markdown("---")

# -----------------------
# Session State
# -----------------------
if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "reg_number" not in st.session_state:
    st.session_state.reg_number = ""
if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None

# -----------------------
# Student Info Form
# -----------------------
if not st.session_state.student_name or not st.session_state.reg_number:
    with st.form("student_form"):
        st.subheader("Enter Your Details to Start Quiz")
        st.session_state.student_name = st.text_input("Full Name")
        st.session_state.reg_number = st.text_input("Registration Number")
        submitted = st.form_submit_button("Start Quiz")
        if submitted:
            if not st.session_state.student_name or not st.session_state.reg_number:
                st.error("Please fill all fields")
            else:
                st.success(f"Welcome {st.session_state.student_name}!")

# -----------------------
# Display Quiz Links
# -----------------------
if st.session_state.student_name and st.session_state.reg_number and not st.session_state.current_quiz:
    st.subheader("Available Quizzes")
    quizzes = load_json(QUIZZES_FILE)
    if quizzes:
        for quiz_name in quizzes:
            st.markdown(f"<a href='#{quiz_name}' style='text-decoration:none; color:white;'><button style='background-color:#4B0082; color:white; padding:10px 20px; border:none; border-radius:8px; margin:5px'>{quiz_name}</button></a>", unsafe_allow_html=True)
            if st.button(f"Take Quiz: {quiz_name}", key=quiz_name):
                st.session_state.current_quiz = quiz_name
    else:
        st.info("No quizzes available at the moment.")

# -----------------------
# Take Quiz Panel
# -----------------------
if st.session_state.current_quiz:
    st.subheader(f"Quiz: {st.session_state.current_quiz}")
    quizzes = load_json(QUIZZES_FILE)
    questions = quizzes[st.session_state.current_quiz]

    user_answers = {}
    for idx, q in enumerate(questions):
        st.markdown(f"**Q{idx+1}: {q['question']}**")
        ans = st.radio("Choose an answer:", q["options"], key=f"{st.session_state.current_quiz}_{idx}")
        user_answers[q['question']] = ans

    if st.button("Submit Quiz"):
        score = sum([1 for q in questions if user_answers[q['question']] == q['answer']])
        results = load_json(RESULTS_FILE)
        quiz_results = results.get(st.session_state.current_quiz, [])
        quiz_results.append({
            "name": st.session_state.student_name,
            "reg_number": st.session_state.reg_number,
            "score": score,
            "answers": user_answers
        })
        results[st.session_state.current_quiz] = quiz_results
        save_json(RESULTS_FILE, results)

        st.success(f"🎉 {st.session_state.student_name}, You scored {score}/{len(questions)}")
        st.balloons()
        st.session_state.current_quiz = None
