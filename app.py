import streamlit as st
import json
import os
import uuid
from urllib.parse import unquote

# -----------------------
# File paths
# -----------------------
QUIZZES_FILE = "data/quizzes.json"
RESULTS_FILE = "data/results.json"
os.makedirs("data", exist_ok=True)

# Initialize files
if not os.path.exists(QUIZZES_FILE):
    with open(QUIZZES_FILE, "w") as f:
        json.dump({}, f)

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
# Page Setup
# -----------------------
st.set_page_config(page_title="Quiz Portal", page_icon="🎓", layout="centered")
st.markdown("<h1 style='text-align:center;color:#4B0082;'>Quiz Portal</h1>", unsafe_allow_html=True)
st.markdown("---")

# -----------------------
# Session State
# -----------------------
if "teacher_logged_in" not in st.session_state:
    st.session_state.teacher_logged_in = False
if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "reg_number" not in st.session_state:
    st.session_state.reg_number = ""
if "current_quiz_id" not in st.session_state:
    st.session_state.current_quiz_id = None

# -----------------------
# Check for quiz link in URL
# -----------------------
query_params = st.experimental_get_query_params()
if "quiz" in query_params:
    st.session_state.current_quiz_id = unquote(query_params["quiz"][0])

# -----------------------
# Teacher Login
# -----------------------
if not st.session_state.teacher_logged_in and not st.session_state.current_quiz_id:
    st.subheader("Teacher Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state.teacher_logged_in = True
            st.success("Logged in as Admin")
        else:
            st.error("Invalid credentials")

# -----------------------
# Teacher Panel
# -----------------------
if st.session_state.teacher_logged_in:
    st.header("Admin Panel - Create Quiz")
    quiz_name = st.text_input("Quiz Name")
    question = st.text_input("Question")
    options = st.text_area("Options (comma separated)")
    answer = st.text_input("Answer")
    
    if st.button("Add Question"):
        if not all([quiz_name, question, options, answer]):
            st.error("Fill all fields!")
        else:
            quizzes = load_json(QUIZZES_FILE)
            quiz_id = str(uuid.uuid4())
            if quiz_id not in quizzes:
                quizzes[quiz_id] = {"name": quiz_name, "questions": []}
            quizzes[quiz_id]["questions"].append({
                "question": question,
                "options": [opt.strip() for opt in options.split(",")],
                "answer": answer.strip()
            })
            save_json(QUIZZES_FILE, quizzes)
            quiz_link = f"{st.get_url()}?quiz={quiz_id}"
            st.success("Question added successfully!")
            st.markdown(f"Share this link with students: [Open Quiz]({quiz_link})")

# -----------------------
# Student Quiz Panel
# -----------------------
if st.session_state.current_quiz_id:
    quizzes = load_json(QUIZZES_FILE)
    quiz_id = st.session_state.current_quiz_id
    if quiz_id not in quizzes:
        st.error("Invalid or expired quiz link")
    else:
        quiz = quizzes[quiz_id]
        st.subheader(f"Quiz: {quiz['name']}")
        
        # Student details form
        if not st.session_state.student_name or not st.session_state.reg_number:
            with st.form("student_form"):
                st.session_state.student_name = st.text_input("Full Name")
                st.session_state.reg_number = st.text_input("Registration Number")
                submitted = st.form_submit_button("Start Quiz")
                if submitted:
                    if not st.session_state.student_name or not st.session_state.reg_number:
                        st.error("Please fill all fields")
                    else:
                        st.success(f"Welcome {st.session_state.student_name}!")
        else:
            # Quiz questions
            user_answers = {}
            for idx, q in enumerate(quiz["questions"]):
                st.markdown(f"**Q{idx+1}: {q['question']}**")
                ans = st.radio("Choose an answer:", q["options"], key=f"{quiz_id}_{idx}")
                user_answers[q['question']] = ans
            
            if st.button("Submit Quiz"):
                score = sum([1 for q in quiz["questions"] if user_answers[q['question']] == q['answer']])
                results = load_json(RESULTS_FILE)
                quiz_results = results.get(quiz_id, [])
                quiz_results.append({
                    "name": st.session_state.student_name,
                    "reg_number": st.session_state.reg_number,
                    "score": score,
                    "answers": user_answers
                })
                results[quiz_id] = quiz_results
                save_json(RESULTS_FILE, results)
                st.success(f"🎉 {st.session_state.student_name}, You scored {score}/{len(quiz['questions'])}")
                st.balloons()
                st.session_state.student_name = ""
                st.session_state.reg_number = ""
                st.session_state.current_quiz_id = None
