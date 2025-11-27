import streamlit as st
import json
import os

# -----------------------
# File paths
# -----------------------
QUIZZES_FILE = "data/quizzes.json"
RESULTS_FILE = "data/results.json"

os.makedirs("data", exist_ok=True)

# Initialize files
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
# Streamlit Page
# -----------------------
st.set_page_config(page_title="Student Quiz Portal", page_icon="🎓", layout="wide")

st.markdown("""
<style>
body {
    background-color: #f0f2f6;
}
h1 {
    color: #4B0082;
    text-align: center;
}
.quiz-card {
    background-color: #4B0082;
    color: white;
    padding: 20px;
    margin: 15px;
    border-radius: 12px;
    text-align: center;
    font-size: 20px;
    font-weight: bold;
    transition: transform 0.2s;
}
.quiz-card:hover {
    transform: scale(1.05);
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>🎓 Student Quiz Portal</h1>", unsafe_allow_html=True)
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
        st.subheader("Enter Your Details")
        st.session_state.student_name = st.text_input("Full Name")
        st.session_state.reg_number = st.text_input("Registration Number")
        submitted = st.form_submit_button("Start")
        if submitted:
            if not st.session_state.student_name or not st.session_state.reg_number:
                st.error("Please fill all fields")
            else:
                st.success(f"Welcome {st.session_state.student_name}!")

# -----------------------
# Quiz Selection (Clickable Cards)
# -----------------------
if st.session_state.student_name and st.session_state.reg_number and not st.session_state.current_quiz:
    st.subheader("Available Quizzes")
    quizzes = load_json(QUIZZES_FILE)
    
    if quizzes:
        cols = st.columns(3)  # 3 cards per row
        for i, quiz_name in enumerate(quizzes.keys()):
            with cols[i % 3]:
                if st.button(quiz_name, key=quiz_name):
                    st.session_state.current_quiz = quiz_name
    else:
        st.info("No quizzes available.")

# -----------------------
# Take Quiz
# -----------------------
if st.session_state.current_quiz:
    st.subheader(f"Quiz: {st.session_state.current_quiz}")
    quiz_questions = load_json(QUIZZES_FILE)[st.session_state.current_quiz]

    user_answers = {}
    for idx, q in enumerate(quiz_questions):
        st.markdown(f"**Q{idx+1}: {q['question']}**")
        ans = st.radio("Choose an answer:", q["options"], key=f"{st.session_state.current_quiz}_{idx}")
        user_answers[q['question']] = ans

    if st.button("Submit Quiz"):
        score = sum([1 for q in quiz_questions if user_answers[q['question']] == q['answer']])
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

        st.success(f"🎉 {st.session_state.student_name}, You scored {score}/{len(quiz_questions)}")
        st.balloons()
        st.session_state.current_quiz = None
