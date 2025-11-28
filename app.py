import streamlit as st
import json, uuid, os, time
from datetime import datetime

# ---------------------------
# Ensure data folder exists
# ---------------------------
if not os.path.exists("data"):
    os.makedirs("data")

QUIZ_FILE = "data/quizzes.json"
RESULT_FILE = "data/results.json"

def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

quizzes = load_json(QUIZ_FILE)
results = load_json(RESULT_FILE)

# ---------------------------
# Streamlit Page Settings
# ---------------------------
st.set_page_config(page_title="Online Quiz Management System", layout="wide")

st.markdown("""
<style>
.quiz-card {
    padding: 20px;
    border-radius: 12px;
    background: #f8f9fa;
    border: 2px solid #eee;
    transition: 0.3s;
}
.quiz-card:hover {
    background: #f0f0f0;
    border-color: #999;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# SESSION STATE
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None

# --------------------------------------------
# ADMIN LOGIN SCREEN
# --------------------------------------------
def admin_login():
    st.title("🔐 Admin Login")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state.logged_in = True
            st.success("Login Successful!")
            st.rerun()
        else:
            st.error("Invalid admin credentials.")

# --------------------------------------------
# ADMIN PANEL
# --------------------------------------------
def admin_panel():
    st.title("👑 Admin Dashboard")

    tab1, tab2, tab3 = st.tabs(["➕ Create Quiz", "📄 Quiz List", "📊 Student Submissions"])

    # ------------------------------
    # ADD QUIZ
    # ------------------------------
    with tab1:
        st.subheader("Create a New Quiz")

        quiz_name = st.text_input("Quiz Name")
        time_limit = st.number_input("Quiz Time Limit (Minutes)", min_value=1, max_value=60, value=5)

        if st.button("Create Quiz"):
            if not quiz_name:
                st.error("Enter quiz name!")
            else:
                quiz_id = str(uuid.uuid4())
                quizzes[quiz_id] = {
                    "name": quiz_name,
                    "time_limit": time_limit,
                    "questions": []
                }
                save_json(QUIZ_FILE, quizzes)

                quiz_link = f"{st.secrets['APP_URL']}?quiz={quiz_id}"

                st.success("Quiz created successfully!")
                st.markdown("### 🔗 Share Quiz Link")
                st.code(quiz_link)

        st.write("---")

        # Add questions to existing quiz
        st.subheader("Add Questions to Quiz")
        quiz_ids = list(quizzes.keys())

        if quiz_ids:
            selected_quiz = st.selectbox("Select Quiz", quiz_ids, format_func=lambda x: quizzes[x]["name"])

            q = st.text_input("Question")
            opts = st.text_input("Options (comma separated)")
            ans = st.text_input("Correct Answer")

            if st.button("Add Question"):
                if q and opts and ans:
                    quizzes[selected_quiz]["questions"].append({
                        "question": q,
                        "options": [o.strip() for o in opts.split(",")],
                        "answer": ans.strip()
                    })
                    save_json(QUIZ_FILE, quizzes)
                    st.success("Question Added!")
                else:
                    st.error("Fill all fields!")
        else:
            st.warning("No quiz exists. Create a quiz first.")

    # ------------------------------
    # VIEW QUIZZES
    # ------------------------------
    with tab2:
        st.subheader("All Quizzes")

        for qid, qdata in quizzes.items():
            with st.container():
                st.markdown(f"<div class='quiz-card'>", unsafe_allow_html=True)
                st.write(f"### {qdata['name']}")
                st.write(f"Time Limit: **{qdata['time_limit']} minutes**")
                st.write(f"Total Questions: **{len(qdata['questions'])}**")
                
                quiz_link = f"{st.secrets['APP_URL']}?quiz={qid}"
                st.code(quiz_link, language="text")
                
                st.markdown("</div>", unsafe_allow_html=True)
                st.write("")

    # ------------------------------
    # VIEW STUDENT RESULTS
    # ------------------------------
    with tab3:
        st.subheader("All Student Submissions")

        if len(results) == 0:
            st.info("No submissions yet.")
        else:
            for rid, rdata in results.items():
                qname = quizzes.get(rdata['quiz_id'], {}).get("name", "Unknown Quiz")
                
                st.markdown(f"""
                ### 🧑 {rdata['name']}  
                **Reg #:** {rdata['regno']}  
                **Quiz:** {qname}  
                **Score:** {rdata['score']}  
                **Date:** {rdata['date']}  
                """)
                st.write("---")

# --------------------------------------------
# STUDENT QUIZ SCREEN
# --------------------------------------------
def student_quiz_page(quiz_id):
    if quiz_id not in quizzes:
        st.error("Invalid quiz link!")
        return

    quiz = quizzes[quiz_id]

    st.title(f"📝 {quiz['name']}")
    st.info(f"⏳ Time Limit: {quiz['time_limit']} Minutes")

    # Student info
    name = st.text_input("Enter Your Name")
    regno = st.text_input("Enter Registration Number")

    if st.button("Start Quiz"):
        if not name or not regno:
            st.error("Enter your details first!")
            return

        st.session_state.current_quiz = quiz_id
        st.session_state.start_time = time.time()
        st.session_state.name = name
        st.session_state.regno = regno
        st.rerun()

    # If quiz started
    if st.session_state.current_quiz == quiz_id:
        start = st.session_state.start_time
        remaining = quiz["time_limit"] * 60 - (time.time() - start)

        if remaining <= 0:
            st.error("⏳ Time is over!")
            return

        st.warning(f"⏰ Time Left: {int(remaining)} seconds")

        answers = {}

        for i, q in enumerate(quiz["questions"]):
            st.write(f"### Q{i+1}. {q['question']}")
            answers[i] = st.radio("", q["options"], key=f"q{i}")

        if st.button("Submit Quiz"):
            score = 0
            for i, q in enumerate(quiz["questions"]):
                if answers[i] == q["answer"]:
                    score += 1

            rid = str(uuid.uuid4())
            results[rid] = {
                "name": st.session_state.name,
                "regno": st.session_state.regno,
                "quiz_id": quiz_id,
                "score": score,
                "date": str(datetime.now())
            }
            save_json(RESULT_FILE, results)

            st.success(f"🎉 Quiz Submitted! Your Score: {score}")
            st.balloons()


# --------------------------------------------
# ROUTER
# --------------------------------------------
query_params = st.query_params

if "quiz" in query_params:
    student_quiz_page(query_params["quiz"])

elif not st.session_state.logged_in:
    admin_login()

else:
    admin_panel()
