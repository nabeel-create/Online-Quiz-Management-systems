import streamlit as st
import json
import os
import uuid
from urllib.parse import unquote
import time

# -----------------------
# File paths
# -----------------------
QUIZZES_FILE = "data/quizzes.json"
RESULTS_FILE = "data/results.json"
os.makedirs("data", exist_ok=True)

# Initialize files if missing
for file_path in [QUIZZES_FILE, RESULTS_FILE]:
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump({}, f)

# -----------------------
# Utility functions
# -----------------------
def load_json(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def generate_quiz_link(quiz_id):
    # Replace with your deployed Streamlit URL
    return f"http://localhost:8501/?quiz={quiz_id}"

# -----------------------
# Page Setup
# -----------------------
st.set_page_config(page_title="Online Quiz System", page_icon="🎓", layout="wide")
st.markdown("""
<style>
h1 { text-align:center; color:#4B0082; }
body { background-color:#f0f2f6; }
.quiz-card {
    background-color:#4B0082; 
    color:white; 
    padding:20px; 
    margin:15px; 
    border-radius:12px; 
    text-align:center; 
    font-size:20px; 
    font-weight:bold;
    transition: transform 0.2s;
}
.quiz-card:hover { transform: scale(1.05); cursor:pointer; }
</style>
""", unsafe_allow_html=True)
st.markdown("<h1>Online Quiz System</h1>", unsafe_allow_html=True)
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
if "start_time" not in st.session_state:
    st.session_state.start_time = None

# -----------------------
# Detect quiz link in URL
# -----------------------
query_params = st.experimental_get_query_params()
if "quiz" in query_params:
    st.session_state.current_quiz_id = unquote(query_params["quiz"][0])

# -----------------------
# Teacher/Admin Login
# -----------------------
if not st.session_state.teacher_logged_in and not st.session_state.current_quiz_id:
    st.subheader("Teacher/Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state.teacher_logged_in = True
            st.success("Logged in as Admin")
        else:
            st.error("Invalid credentials")

# -----------------------
# Teacher/Admin Dashboard
# -----------------------
if st.session_state.teacher_logged_in:
    st.header("Admin Dashboard")

    # --- Create New Quiz ---
    with st.expander("📌 Create New Quiz"):
        quiz_name = st.text_input("Quiz Name")
        question = st.text_input("Question")
        options = st.text_area("Options (comma separated)")
        answer = st.text_input("Answer")
        time_limit = st.number_input("Time Limit (minutes)", min_value=1, max_value=180, value=5)
        if st.button("Add Question"):
            if not all([quiz_name, question, options, answer]):
                st.error("Fill all fields!")
            else:
                quizzes = load_json(QUIZZES_FILE)
                quiz_id = str(uuid.uuid4())
                quizzes[quiz_id] = {"name": quiz_name, "questions": [{
                    "question": question,
                    "options": [opt.strip() for opt in options.split(",")],
                    "answer": answer.strip()
                }], "time_limit": time_limit}
                save_json(QUIZZES_FILE, quizzes)
                link = generate_quiz_link(quiz_id)
                st.success("Quiz created successfully!")
                st.markdown(f"Share this link with students: [Open Quiz]({link})")

    # --- View Existing Quizzes ---
    st.subheader("All Quizzes")
    quizzes = load_json(QUIZZES_FILE)
    if quizzes:
        for quiz_id, quiz in quizzes.items():
            if isinstance(quiz, dict) and 'name' in quiz:
                time_limit = quiz.get('time_limit', 5)
                st.markdown(f"**{quiz['name']}** (Time: {time_limit} min)")
                link = generate_quiz_link(quiz_id)
                st.markdown(f"Link: [Open Quiz]({link})")
                results = load_json(RESULTS_FILE).get(quiz_id, [])
                if results:
                    with st.expander("View Results"):
                        for res in results:
                            st.write(f"{res['name']} ({res['reg_number']}): {res['score']}/{len(quiz['questions'])}")
                st.markdown("---")
            else:
                st.error("Invalid quiz data detected.")

# -----------------------
# Student Quiz Panel
# -----------------------
if st.session_state.current_quiz_id is None:
    st.subheader("Available Quizzes")
    quizzes = load_json(QUIZZES_FILE)
    if quizzes:
        cols = st.columns(3)
        for i, (quiz_id, quiz) in enumerate(quizzes.items()):
            if isinstance(quiz, dict) and 'name' in quiz:
                with cols[i % 3]:
                    if st.button(quiz["name"], key=quiz_id):
                        st.session_state.current_quiz_id = quiz_id
    else:
        st.info("No quizzes available yet.")

# -----------------------
# Take Quiz
# -----------------------
if st.session_state.current_quiz_id:
    quizzes = load_json(QUIZZES_FILE)
    quiz_id = st.session_state.current_quiz_id
    quiz = quizzes.get(quiz_id, None)
    if not quiz or not isinstance(quiz, dict):
        st.error("Invalid or expired quiz link")
    else:
        st.subheader(f"Quiz: {quiz['name']} (Time: {quiz.get('time_limit',5)} min)")

        # --- Student info ---
        if not st.session_state.student_name or not st.session_state.reg_number:
            with st.form("student_form"):
                st.session_state.student_name = st.text_input("Full Name")
                st.session_state.reg_number = st.text_input("Registration Number")
                submitted = st.form_submit_button("Start Quiz")
                if submitted:
                    if not st.session_state.student_name or not st.session_state.reg_number:
                        st.error("Please fill all fields")
                    else:
                        st.session_state.start_time = time.time()
                        st.success(f"Welcome {st.session_state.student_name}!")
        else:
            # Check previous attempts
            results_data = load_json(RESULTS_FILE).get(quiz_id, [])
            if any(r["reg_number"] == st.session_state.reg_number for r in results_data):
                st.warning("You have already attempted this quiz.")
            else:
                # Initialize start_time if None
                if st.session_state.start_time is None:
                    st.session_state.start_time = time.time()

                # Timer
                time_limit_seconds = quiz.get("time_limit",5)*60
                elapsed = time.time() - st.session_state.start_time
                remaining = int(time_limit_seconds - elapsed)
                auto_submit = False
                if remaining <= 0:
                    st.warning("Time is up! Submitting your quiz...")
                    remaining = 0
                    auto_submit = True
                else:
                    st.info(f"Time Remaining: {remaining//60} min {remaining%60} sec")

                # Quiz questions
                user_answers = {}
                for idx, q in enumerate(quiz["questions"]):
                    st.markdown(f"**Q{idx+1}: {q['question']}**")
                    ans = st.radio("Choose an answer:", q["options"], key=f"{quiz_id}_{idx}")
                    user_answers[q['question']] = ans

                if st.button("Submit Quiz") or auto_submit:
                    score = sum([1 for q in quiz["questions"] if user_answers[q['question']] == q['answer']])
                    results_data = load_json(RESULTS_FILE)
                    quiz_results = results_data.get(quiz_id, [])
                    quiz_results.append({
                        "name": st.session_state.student_name,
                        "reg_number": st.session_state.reg_number,
                        "score": score,
                        "answers": user_answers
                    })
                    results_data[quiz_id] = quiz_results
                    save_json(RESULTS_FILE, results_data)
                    st.success(f"🎉 {st.session_state.student_name}, You scored {score}/{len(quiz['questions'])}")
                    st.balloons()
                    # Reset state
                    st.session_state.student_name = ""
                    st.session_state.reg_number = ""
                    st.session_state.current_quiz_id = None
                    st.session_state.start_time = None
