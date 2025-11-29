import streamlit as st
import json, uuid, os, time, math
from datetime import datetime
import pandas as pd
from openrouter import OpenRouter

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
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

quizzes = load_json(QUIZ_FILE)
results = load_json(RESULT_FILE)

# ---------------------------
# OpenRouter Mistral 7B Setup
# ---------------------------
try:
    api_key = st.secrets["openrouter"]["api_key"]
    openrouter = OpenRouter(api_key=api_key)
    OPENROUTER_AVAILABLE = True
except:
    st.warning("OpenRouter API key not found in secrets. AI features disabled.")
    OPENROUTER_AVAILABLE = False

# ---------------------------
# AI MCQ Generation
# ---------------------------
def generate_mcqs_from_text_ai(text, num_questions=5):
    mcqs = []
    if not OPENROUTER_AVAILABLE:
        st.error("OpenRouter not available. Cannot generate MCQs.")
        return mcqs

    prompt = f"""
Extract {num_questions} multiple-choice questions (MCQs) from the following text.
Return as a JSON array with each element like:
{{
  "question": "...",
  "options": ["...","...","...","..."],
  "answer": "...",
  "description": "..."
}}
Text:
{text}
"""

    try:
        # Streamed response
        stream = openrouter.chat.send(
            model="mistralai/mistral-7b-instruct:free",
            messages=[{"role":"user","content":prompt}],
            stream=True
        )

        ai_text = ""
        for chunk in stream:
            delta = chunk.choices[0].delta.get("content") if chunk.choices else None
            if delta:
                ai_text += delta
                # Optional: show live in Streamlit
                st.write(delta)

        mcqs = json.loads(ai_text)
    except Exception as e:
        st.error(f"Error generating MCQs: {e}")
        st.info("Try shorter text or fewer questions.")
    return mcqs

# ---------------------------
# Admin: Create Quiz / Add AI MCQs
# ---------------------------
st.title("👑 Admin Dashboard")

quiz_name = st.text_input("Quiz Name")
time_limit = st.number_input("Time Limit (Minutes)", 1, 60, 5)
if st.button("Create Quiz"):
    if quiz_name:
        quiz_id = str(uuid.uuid4())
        quizzes[quiz_id] = {"name": quiz_name, "time_limit": time_limit, "questions": []}
        save_json(QUIZ_FILE, quizzes)
        st.success("✅ Quiz Created!")

st.write("---")
st.subheader("Generate AI MCQs")
if quizzes:
    selected = st.selectbox("Select Quiz", list(quizzes.keys()), format_func=lambda x: quizzes[x]["name"])
    text_input = st.text_area("Paste Text Here")
    num_questions = st.number_input("Number of MCQs to generate", 1, 10, 5)
    if st.button("Generate MCQs"):
        if text_input.strip():
            with st.spinner("Generating MCQs..."):
                new_qs = generate_mcqs_from_text_ai(text_input, num_questions)
            if new_qs:
                quizzes[selected]["questions"].extend(new_qs)
                save_json(QUIZ_FILE, quizzes)
                st.success(f"✅ {len(new_qs)} MCQs added!")
        else:
            st.error("Enter text for MCQs!")

# ---------------------------
# Student: Take Quiz
# ---------------------------
params = st.experimental_get_query_params()
quiz_id = params.get("quiz", [None])[0]

if quiz_id:
    if quiz_id not in quizzes:
        st.error("Invalid Quiz!")
    else:
        quiz = quizzes[quiz_id]
        st.title(f"📝 {quiz['name']}")
        st.info(f"Time Limit: {quiz['time_limit']} min")
        if "started" not in st.session_state:
            st.session_state.started = False
        if not st.session_state.started:
            name = st.text_input("Your Name")
            regno = st.text_input("Registration Number")
            if st.button("Start Quiz"):
                if name and regno:
                    st.session_state.started = True
                    st.session_state.current_quiz = quiz_id
                    st.session_state.name = name
                    st.session_state.regno = regno
                    st.session_state.answers = {}
                    st.session_state.question_index = 0
                    st.session_state.start_time = time.time()
                    st.experimental_rerun()
        else:
            total_seconds = quiz["time_limit"]*60
            elapsed = time.time() - st.session_state.start_time
            remaining = total_seconds - elapsed
            st.write(f"⏳ Time Left: {int(remaining)} seconds")
            idx = st.session_state.question_index
            q = quiz["questions"][idx]
            choice = st.radio(f"Q{idx+1}: {q['question']}", q["options"], key=f"q{idx}")
            st.session_state.answers[idx] = choice
            col1, col2 = st.columns(2)
            with col1:
                if idx > 0 and st.button("⬅ Previous"):
                    st.session_state.question_index -= 1
                    st.experimental_rerun()
            with col2:
                if idx < len(quiz["questions"]) - 1 and st.button("Next ➡"):
                    st.session_state.question_index += 1
                    st.experimental_rerun()
                elif idx == len(quiz["questions"]) - 1 and st.button("Submit"):
                    score = sum(1 for i,q in enumerate(quiz["questions"]) if st.session_state.answers.get(i)==q["answer"])
                    rid = str(uuid.uuid4())
                    results[rid] = {
                        "name": st.session_state.name,
                        "regno": st.session_state.regno,
                        "quiz_id": quiz_id,
                        "score": score,
                        "date": str(datetime.now())
                    }
                    save_json(RESULT_FILE, results)
                    st.success(f"🎉 Quiz Submitted! Score: {score}/{len(quiz['questions'])}")
