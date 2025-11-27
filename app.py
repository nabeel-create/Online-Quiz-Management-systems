import streamlit as st
import json
import bcrypt

# -----------------------
# File paths
# -----------------------
USERS_FILE = "data/users.json"
QUIZZES_FILE = "data/quizzes.json"
RESULTS_FILE = "data/results.json"

# -----------------------
# Utility functions
# -----------------------
def load_json(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# -----------------------
# Load data
# -----------------------
users = load_json(USERS_FILE)
quizzes = load_json(QUIZZES_FILE)
results = load_json(RESULTS_FILE)

# -----------------------
# Streamlit page setup
# -----------------------
st.set_page_config(page_title="Quiz Management System", page_icon="📝", layout="centered")
st.title("📝 Online Quiz Management System")

# -----------------------
# Sidebar Authentication
# -----------------------
st.sidebar.title("Login / SignUp")
auth_choice = st.sidebar.radio("Choose Action", ["Login", "SignUp"])

if auth_choice == "SignUp":
    st.subheader("Create New Account")
    new_username = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["user", "admin"])
    
    if st.button("Sign Up"):
        if new_username in users:
            st.error("Username already exists!")
        elif not new_username or not new_password:
            st.error("Enter valid username and password.")
        else:
            users[new_username] = {"password": hash_password(new_password), "role": role}
            save_json(USERS_FILE, users)
            st.success("Account created! You can login now.")

elif auth_choice == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username in users and check_password(password, users[username]["password"]):
            st.success(f"Logged in as {username}")
            user_role = users[username]["role"]

            # -----------------------
            # Admin Panel
            # -----------------------
            if user_role == "admin":
                st.header("Admin Panel 🛠️")
                
                # Create new quiz question
                st.subheader("Add New Question")
                quiz_name = st.text_input("Quiz Name", key="quiz_name")
                question_text = st.text_input("Question", key="question_text")
                options_text = st.text_area("Options (comma separated)", key="options_text")
                answer_text = st.text_input("Answer", key="answer_text")
                
                if st.button("Add Question"):
                    if not all([quiz_name, question_text, options_text, answer_text]):
                        st.error("Please fill all fields")
                    else:
                        if quiz_name not in quizzes:
                            quizzes[quiz_name] = []
                        quizzes[quiz_name].append({
                            "question": question_text,
                            "options": [opt.strip() for opt in options_text.split(",")],
                            "answer": answer_text.strip()
                        })
                        save_json(QUIZZES_FILE, quizzes)
                        st.success("Question added successfully!")

                # View all quizzes
                st.subheader("All Quizzes")
                for qname, qlist in quizzes.items():
                    st.write(f"**{qname}**")
                    for idx, q in enumerate(qlist):
                        st.write(f"{idx+1}. {q['question']} | Answer: {q['answer']}")
                
                # View quiz results
                st.subheader("Quiz Results")
                for qname, res in results.items():
                    st.write(f"**{qname}**")
                    for user, data in res.items():
                        st.write(f"- {user}: {data['score']}/{len(quizzes[qname])}")

            # -----------------------
            # User Panel
            # -----------------------
            else:
                st.header("User Panel 🎯")
                
                if not quizzes:
                    st.info("No quizzes available. Please check back later.")
                else:
                    quiz_choice = st.selectbox("Select Quiz", list(quizzes.keys()))
                    
                    if quiz_choice:
                        user_score = 0
                        user_answers = {}
                        st.subheader(f"Quiz: {quiz_choice}")
                        for idx, q in enumerate(quizzes[quiz_choice]):
                            st.write(f"Q{idx+1}: {q['question']}")
                            ans = st.radio("Choose an answer:", q["options"], key=f"{quiz_choice}_{idx}")
                            user_answers[q['question']] = ans
                            if ans == q['answer']:
                                user_score += 1
                        
                        if st.button("Submit Quiz"):
                            if quiz_choice not in results:
                                results[quiz_choice] = {}
                            results[quiz_choice][username] = {"score": user_score, "answers": user_answers}
                            save_json(RESULTS_FILE, results)
                            st.success(f"You scored {user_score}/{len(quizzes[quiz_choice])}")
        else:
            st.error("Invalid Username or Password")
