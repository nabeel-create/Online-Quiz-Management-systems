import streamlit as st
import json, uuid, os, time, math
from datetime import datetime
import pandas as pd
import altair as alt
from streamlit_autorefresh import st_autorefresh
import random

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
st.set_page_config(page_title="Online Quiz System", layout="wide")

# ---------------------------
# CSS Styling
# ---------------------------
st.markdown("""
<style>
body { transition: background-color 0.5s, color 0.5s; }
.quiz-card {
    padding: 15px;
    border-radius: 12px;
    background: #f8f9fa;
    border: 2px solid #eee;
    margin-bottom: 15px;
    transition: 0.3s;
}
.quiz-card:hover { background: #f0f0f0; border-color: #999; }
.dark .quiz-card { background: #2e2e2e; color: white; border-color: #555; }
.button-style { background-color: #4CAF50; color: white; padding: 10px 20px; font-size: 16px; border-radius: 8px; }
@media only screen and (max-width: 768px) { .quiz-card { padding: 10px; } .button-style { width: 100%; } }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# SESSION STATE
# ---------------------------
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_quiz" not in st.session_state: st.session_state.current_quiz = None
if "start_time" not in st.session_state: st.session_state.start_time = None
if "theme" not in st.session_state: st.session_state.theme = "light"
if "question_index" not in st.session_state: st.session_state.question_index = 0
if "quiz_started" not in st.session_state: st.session_state.quiz_started = False
if "answers" not in st.session_state: st.session_state.answers = {}

# ---------------------------
# BASE URL (Secrets + fallback)
# ---------------------------
def get_base_url():
    try: return st.secrets["APP_URL"]
    except: return "http://localhost:8501"

BASE_URL = get_base_url()

# ---------------------------
# Theme Toggle
# ---------------------------
def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme=="light" else "light"

if st.button("Toggle Dark/Light Theme"): toggle_theme()
if st.session_state.theme == "dark": st.markdown("<body class='dark'>", unsafe_allow_html=True)

# ---------------------------
# Admin Login
# ---------------------------
def admin_login():
    st.title("🔐 Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username=="admin" and password=="admin123":
            st.session_state.logged_in = True
            st.success("Login Successful!")
            st.rerun()
        else:
            st.error("Invalid credentials!")

# ---------------------------
# Extract MCQs from Text
# ---------------------------
def extract_mcqs_from_text(text, n=5):
    """
    Simple MCQ extraction from text.
    For real implementation, you can integrate GPT or NLP to generate questions.
    Currently, it takes sentences and creates placeholder options.
    """
    lines = [line.strip() for line in text.split(".") if line.strip()]
    mcqs = []
    for i in range(min(n, len(lines))):
        question = lines[i] + "?"
        # Simple placeholder options
        options = ["Option A", "Option B", "Option C", "Option D"]
        # Randomly pick one as correct answer (can improve later)
        answer = random.choice(options)
        description = lines[i]
        mcqs.append({"question": question, "options": options, "answer": answer, "description": description})
    return mcqs

# ---------------------------
# Circular Timer
# ---------------------------
def circular_timer(seconds_left, total_seconds):
    pct = seconds_left/total_seconds
    radius = 80
    color = "#4CAF50" if pct>0.2 else "#FF0000"
    svg = f"""
    <svg width="200" height="200">
      <circle cx="100" cy="100" r="{radius}" fill="none" stroke="#eee" stroke-width="15"/>
      <circle cx="100" cy="100" r="{radius}" fill="none" stroke="{color}" stroke-width="15"
        stroke-dasharray="{2*math.pi*radius*pct}, {2*math.pi*radius}"/>
      <text x="100" y="110" text-anchor="middle" font-size="24" fill="black">{int(seconds_left)}s</text>
    </svg>
    """
    st.markdown(svg, unsafe_allow_html=True)

# ---------------------------
# Student Quiz Page
# ---------------------------
def student_quiz_page(quiz_id):
    if quiz_id not in quizzes:
        st.error("Invalid Quiz!")
        return
    quiz = quizzes[quiz_id]
    st.title(f"📝 {quiz['name']}")
    st.info(f"Time Limit: {quiz['time_limit']} min")

    if not st.session_state.quiz_started:
        name = st.text_input("Your Name")
        regno = st.text_input("Registration Number")
        if st.button("Start Quiz"):
            if not name or not regno: st.error("Enter details!"); return
            st.session_state.current_quiz = quiz_id
            st.session_state.start_time = time.time()
            st.session_state.name = name
            st.session_state.regno = regno
            st.session_state.question_index = 0
            st.session_state.answers = {}
            st.session_state.quiz_started = True
            st.rerun()
    else:
        start = st.session_state.start_time
        total_seconds = quiz["time_limit"]*60
        remaining = total_seconds - (time.time()-start)
        if remaining<=0: 
            st.error("⏳ Time Over!"); 
            st.session_state.quiz_started=False
            return
        
        circular_timer(remaining,total_seconds)

        idx = st.session_state.question_index
        q = quiz["questions"][idx]
        st.write(f"Q{idx+1}/{len(quiz['questions'])}: {q['question']}")
        choice = st.radio("", q["options"], key=f"q{idx}")
        st.session_state.answers[idx] = choice

        col1,col2 = st.columns(2)
        with col1:
            if idx>0 and st.button("⬅ Previous"): 
                st.session_state.question_index-=1
                st.rerun()
        with col2:
            if idx<len(quiz["questions"])-1 and st.button("Next ➡"): 
                st.session_state.question_index+=1
                st.rerun()
            elif idx==len(quiz["questions"])-1 and st.button("Submit Quiz"):
                # Calculate score
                score=sum(1 for i,q in enumerate(quiz["questions"]) if st.session_state.answers.get(i)==q["answer"])
                rid=str(uuid.uuid4())
                results[rid]={"name":st.session_state.name,"regno":st.session_state.regno,"quiz_id":quiz_id,"score":score,"date":str(datetime.now())}
                save_json(RESULT_FILE,results)
                
                st.success(f"🎉 Quiz Submitted! Score: {score}/{len(quiz['questions'])}")
                
                # Show descriptions/explanations
                st.write("### ✅ Answer Explanations:")
                for i, q in enumerate(quiz["questions"]):
                    st.write(f"**Q{i+1}: {q['question']}**")
                    st.write(f"Your Answer: {st.session_state.answers.get(i,'Not Answered')}")
                    st.write(f"Correct Answer: {q['answer']}")
                    st.write(f"Explanation: {q.get('description','No explanation provided')}")
                    st.write("---")
                
                st.balloons()
                st.session_state.quiz_started=False

# ---------------------------
# Admin Dashboard
# ---------------------------
def admin_panel():
    st.title("👑 Admin Dashboard")
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Create Quiz", "📄 Quiz List", "📊 Live Student Results", "📈 Analytics"])

    with tab1:
        st.subheader("Create New Quiz")
        quiz_name = st.text_input("Quiz Name")
        time_limit = st.number_input("Time Limit (Minutes)", 1, 60, 5)
        if st.button("Create Quiz"):
            if not quiz_name: st.error("Enter quiz name!")
            else:
                quiz_id = str(uuid.uuid4())
                quizzes[quiz_id] = {"name":quiz_name, "time_limit":time_limit, "questions":[]}
                save_json(QUIZ_FILE, quizzes)
                st.success("✅ Quiz Created!")
                st.text_input("Share Link:", f"{BASE_URL}?quiz={quiz_id}")

        st.write("---")
        st.subheader("Add Questions Manually")
        if quizzes:
            selected = st.selectbox("Select Quiz", list(quizzes.keys()), format_func=lambda x: quizzes[x]["name"])
            q = st.text_input("Question")
            opts = st.text_input("Options (comma separated)")
            ans = st.text_input("Correct Answer")
            desc = st.text_input("Description/Explanation")
            if st.button("Add Question"):
                if q and opts and ans:
                    quizzes[selected]["questions"].append({"question":q,"options":[o.strip() for o in opts.split(",")],"answer":ans.strip(),"description":desc})
                    save_json(QUIZ_FILE, quizzes)
                    st.success("✅ Question added!")
                else: st.error("Fill all fields!")
        else: st.info("No quizzes yet.")

        st.write("---")
        st.subheader("Auto-generate MCQs from Description/Text")
        if quizzes:
            selected = st.selectbox("Select Quiz to Add Generated MCQs", list(quizzes.keys()), format_func=lambda x: quizzes[x]["name"])
            text_input = st.text_area("Paste Description/Text Here")
            num_questions = st.number_input("Number of MCQs to generate", 1, 20, 5)
            if st.button("Extract MCQs from Text"):
                if not text_input.strip():
                    st.error("Please provide text!")
                else:
                    new_qs = extract_mcqs_from_text(text_input, num_questions)
                    quizzes[selected]["questions"].extend(new_qs)
                    save_json(QUIZ_FILE, quizzes)
                    st.success(f"{len(new_qs)} MCQs added to {quizzes[selected]['name']}!")

    with tab2:
        st.subheader("All Quizzes")
        for qid,qdata in quizzes.items():
            with st.container():
                st.markdown(f"<div class='quiz-card'>", unsafe_allow_html=True)
                st.write(f"### {qdata['name']}")
                st.write(f"Time Limit: **{qdata['time_limit']} min**")
                st.write(f"Questions: **{len(qdata['questions'])}**")
                st.code(f"{BASE_URL}?quiz={qid}")
                st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.subheader("Live Student Submissions")
        st_autorefresh(interval=5000, key="live_refresh")  # refresh every 5 sec
        if results:
            df = pd.DataFrame.from_dict(results, orient="index")
            st.dataframe(df)
            avg_score = df['score'].mean()
            st.metric("Average Score", f"{avg_score:.2f}")
            st.metric("Total Submissions", len(df))
        else:
            st.info("No submissions yet.")

    with tab4:
        st.subheader("Quiz Analytics")
        if results:
            df = pd.DataFrame.from_dict(results, orient="index")
            chart = alt.Chart(df).mark_bar().encode(
                x="quiz_id:N", y="score:Q", color="quiz_id:N", tooltip=["name","score"]
            )
            st.altair_chart(chart, use_container_width=True)
        else: st.info("No data yet.")

# ---------------------------
# Router
# ---------------------------
params = st.experimental_get_query_params()
quiz_id = params.get("quiz",[None])[0]

if quiz_id: 
    student_quiz_page(quiz_id)
elif not st.session_state.logged_in: 
    admin_login()
else: 
    admin_panel()
