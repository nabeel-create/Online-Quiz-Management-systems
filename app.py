import streamlit as st
import json, uuid, os, time, math, random
from datetime import datetime
import pandas as pd
import altair as alt
from fpdf import FPDF
from streamlit_autorefresh import st_autorefresh

# Optional AI (OpenRouter)
try:
    from openrouter import OpenRouter
    OPENROUTER_AVAILABLE = True
except ModuleNotFoundError:
    OPENROUTER_AVAILABLE = False

# Ensure data folder exists
if not os.path.exists("data"):
    os.makedirs("data")

QUIZ_FILE = "data/quizzes.json"
RESULT_FILE = "data/results.json"
USERS_FILE = "data/users.json"
BANK_FILE = "data/question_bank.json"

def load_json(path):
    if not os.path.exists(path): return {}
    try:
        with open(path, "r") as f: return json.load(f)
    except: return {}

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=4)

quizzes = load_json(QUIZ_FILE)
results = load_json(RESULT_FILE)
users = load_json(USERS_FILE)
question_bank = load_json(BANK_FILE)

# Streamlit Page Settings
st.set_page_config(page_title="AI Quiz System", layout="wide")

# CSS Styling
st.markdown("""
<style>
body { transition: background-color 0.5s, color 0.5s; }
.quiz-card { padding:15px; border-radius:12px; background:#f8f9fa; border:2px solid #eee; margin-bottom:15px; transition:0.3s; }
.quiz-card:hover { background:#f0f0f0; border-color:#999; }
.dark .quiz-card { background:#2e2e2e; color:white; border-color:#555; }
.button-style { background-color:#4CAF50; color:white; padding:10px 20px; font-size:16px; border-radius:8px; }
@media only screen and (max-width:768px) { .quiz-card { padding:10px; } .button-style { width:100%; } }
</style>
""", unsafe_allow_html=True)

# Session State
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "current_quiz" not in st.session_state: st.session_state.current_quiz = None
if "start_time" not in st.session_state: st.session_state.start_time = None
if "theme" not in st.session_state: st.session_state.theme = "light"
if "question_index" not in st.session_state: st.session_state.question_index = 0
if "quiz_started" not in st.session_state: st.session_state.quiz_started = False
if "answers" not in st.session_state: st.session_state.answers = {}

# Theme Toggle
def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme=="light" else "light"

if st.button("Toggle Dark/Light Theme"): toggle_theme()
if st.session_state.theme == "dark": st.markdown("<body class='dark'>", unsafe_allow_html=True)

# Admin Login
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

# OpenRouter AI Setup
if OPENROUTER_AVAILABLE:
    try:
        api_key = st.secrets["openrouter"]["api_key"]
        openrouter = OpenRouter(api_key=api_key)
    except:
        st.warning("OpenRouter API key not found in secrets. AI MCQ generation disabled.")
        OPENROUTER_AVAILABLE = False

# AI MCQ Generation
def generate_mcqs_from_text_ai(text, num_questions=5):
    mcqs = []
    if not OPENROUTER_AVAILABLE:
        st.error("OpenRouter not available. Cannot generate MCQs.")
        return mcqs

    prompt = f"""
Extract {num_questions} multiple-choice questions (MCQs) from the following text.
Return the result as a JSON array:
{{ "question": "...", "type":"mcq", "options":["...","...","...","..."], "answer":"...", "description":"..." }}
Text:
{text}
"""
    try:
        response = openrouter.chat.send(
            model="google/gemma-3n-e2b-it:free",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        ai_text = response.choices[0].message.get("content","")
        mcqs = json.loads(ai_text)
    except Exception as e:
        st.error(f"Error generating MCQs: {e}")
        st.info("AI may not have returned valid JSON. Try shorter text or fewer questions.")
    return mcqs

# Circular Timer
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

# Submit Quiz
def submit_quiz(quiz, answers):
    score = 0
    for i,q in enumerate(quiz["questions"]):
        user_ans = answers.get(i,"")
        if q["type"] in ["mcq","true_false","fill_blank"]:
            if user_ans.strip().lower() == q["answer"].strip().lower():
                score+=1
        else: # short_answer (manual check)
            if user_ans.strip():
                score+=1
    rid = str(uuid.uuid4())
    results[rid] = {"name":st.session_state.name,"regno":st.session_state.regno,"quiz_id":st.session_state.current_quiz,"score":score,"date":str(datetime.now())}
    save_json(RESULT_FILE, results)
    return score

# Student Quiz Page
def student_quiz_page(quiz_id):
    if quiz_id not in quizzes: st.error("Invalid Quiz!"); return
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
            st.warning("⏳ Time Over! Auto-submitting...")
            score = submit_quiz(quiz, st.session_state.answers)
            st.success(f"🎉 Quiz Submitted! Score: {score}/{len(quiz['questions'])}")
            st.session_state.quiz_started=False
            return
        
        circular_timer(remaining,total_seconds)

        if "shuffled_questions" not in st.session_state:
            st.session_state.shuffled_questions = quiz["questions"].copy()
            random.shuffle(st.session_state.shuffled_questions)

        idx = st.session_state.question_index
        q = st.session_state.shuffled_questions[idx]

        st.write(f"Q{idx+1}/{len(quiz['questions'])}: {q['question']}")
        if q["type"]=="mcq":
            opts = q["options"].copy()
            random.shuffle(opts)
            choice = st.radio("", opts, key=f"q{idx}")
            st.session_state.answers[idx] = choice
        elif q["type"]=="true_false":
            choice = st.radio("", ["True","False"], key=f"q{idx}")
            st.session_state.answers[idx] = choice
        elif q["type"] in ["fill_blank","short_answer"]:
            answer = st.text_input("Your Answer", key=f"q{idx}")
            st.session_state.answers[idx] = answer

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
                score = submit_quiz(quiz, st.session_state.answers)
                st.success(f"🎉 Quiz Submitted! Score: {score}/{len(quiz['questions'])}")
                st.write("### ✅ Answer Explanations:")
                for i, q in enumerate(quiz["questions"]):
                    st.write(f"**Q{i+1}: {q['question']}**")
                    st.write(f"Your Answer: {st.session_state.answers.get(i,'Not Answered')}")
                    st.write(f"Correct Answer: {q['answer']}")
                    st.write(f"Explanation: {q.get('description','No explanation')}")
                    st.write("---")
                st.balloons()
                st.session_state.quiz_started=False

# Admin Panel
def admin_panel():
    st.title("👑 Admin Dashboard")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Create Quiz","📄 Quiz List","📊 Live Results","📈 Analytics","🧠 AI Tools"])

    with tab5:
        st.subheader("AI MCQs / Chat Tutor")

        # OpenRouter AI
        if OPENROUTER_AVAILABLE:
            if quizzes:
                selected = st.selectbox(
                    "Select Quiz for AI-generated MCQs",
                    list(quizzes.keys()),
                    format_func=lambda x: quizzes[x]["name"]
                )
                text_input = st.text_area("Paste Text/Slides Here")
                num_questions = st.number_input("Number of MCQs", 1, 10, 5)
                if st.button("Generate AI MCQs"):
                    if text_input.strip():
                        new_qs = generate_mcqs_from_text_ai(text_input, num_questions)
                        if new_qs:
                            quizzes[selected]["questions"].extend(new_qs)
                            save_json(QUIZ_FILE, quizzes)
                            st.success(f"{len(new_qs)} AI MCQs added!")
                        else:
                            st.warning("No MCQs generated.")

            question = st.text_input("Ask AI Tutor")
            if st.button("Get Answer"):
                if question.strip():
                    response = openrouter.chat.send(
                        model="google/gemma-3n-e2b-it:free",
                        messages=[{"role": "user", "content": question}]
                    )
                    st.write(response.choices[0].message["content"])
        else:
            st.info("OpenRouter not available. Add API key in secrets for AI features.")

        # Puter AI Demo
        st.markdown("---")
        st.subheader("Puter AI Chat Demo")
        puter_prompt = st.text_input("Enter prompt for Puter AI", "Write a short poem about coding")
        if st.button("Run Puter AI Prompt"):
            puter_html = f"""
            <html>
            <body>
                <script src="https://js.puter.com/v2/"></script>
                <script>
                    const models = ["gpt-5.1","gpt-5","gpt-5-nano","gpt-5-mini","gpt-5-chat-latest"];
                    models.forEach(model => {{
                        puter.ai.chat("{puter_prompt}", {{ model: model }}).then(response => {{
                            puter.print("<h4>Model: "+model+"</h4>");
                            puter.print(response);
                        }});
                    }});
                </script>
            </body>
            </html>
            """
            import streamlit.components.v1 as components
            components.html(puter_html, height=500)

# Router
params = st.experimental_get_query_params()
quiz_id = params.get("quiz",[None])[0]

if quiz_id: 
    student_quiz_page(quiz_id)
elif not st.session_state.logged_in: 
    admin_login()
else: 
    admin_panel()
