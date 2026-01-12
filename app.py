import streamlit as st
import tempfile
import os
import time
from collections import Counter

from resume_engine.run_pipeline import run
from resume_engine.question_generator import generate_question
from resume_engine.answer_evaluator import evaluate_answer
from resume_engine.next_question_policy import decide_next_level

# ------------------ CONFIG ------------------
MAX_QUESTIONS = 6          # hard cap
MIN_QUESTIONS = 2          # minimum before early stop
TYPE_DELAY = 0.03          # typing speed

# ------------------ Page Setup ------------------
st.set_page_config(
    page_title="ARES – AI Interview Simulator",
    layout="wide"
)

st.title("🧠 ARES – AI Resume-Based Interview System")
st.caption("Upload a resume and experience a realistic AI-driven technical interview")

# ------------------ TYPING EFFECT ------------------
def typewriter(text, delay=TYPE_DELAY):
    placeholder = st.empty()
    rendered = ""
    for word in text.split():
        rendered += word + " "
        placeholder.markdown(rendered)
        time.sleep(delay)

# ------------------ CACHED HELPERS ------------------
@st.cache_data(show_spinner=False)
def cached_run(resume_bytes):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(resume_bytes)
        path = tmp.name
    profile, interview_state = run(path)
    os.remove(path)
    return profile, interview_state


@st.cache_data(show_spinner=False)
def cached_generate_question(skill, depth, asked):
    return generate_question(skill, depth, tuple(asked))


# ------------------ ADAPTIVE STOPPING LOGIC ------------------
def should_end_interview(history):
    """
    Adaptive interview termination policy.
    Returns True if interview should stop.
    """

    n = len(history)
    if n < MIN_QUESTIONS:
        return False

    # ---- Rule 1: Hard cap ----
    if n >= MAX_QUESTIONS:
        return True

    verdicts = [turn["quality"]["quality"] for turn in history]

    # ---- Rule 2: Two strong answers in a row ----
    if n >= 2 and verdicts[-1] == "Strong" and verdicts[-2] == "Strong":
        return True

    # ---- Rule 3: Confidence stabilized (same verdict twice) ----
    if n >= 2 and verdicts[-1] == verdicts[-2]:
        return True

    # ---- Rule 4: Repeated missing concepts ----
    missing = []
    for turn in history:
        concepts = turn["quality"].get("concepts")
        if concepts:
            missing.extend(concepts.get("missing", []))

    missing_counter = Counter(missing)
    for _, freq in missing_counter.items():
        if freq >= 2:
            return True

    return False


# ------------------ File Upload ------------------
uploaded_file = st.file_uploader(
    "Upload your Resume (PDF or DOCX)",
    type=["pdf", "docx"]
)

if uploaded_file:

    # ------------------ Resume Analysis ------------------
    if "profile" not in st.session_state:
        with st.spinner("Analyzing resume and preparing interview..."):
            try:
                profile, interview_state = cached_run(uploaded_file.getvalue())
            except ValueError as e:
                st.error(str(e))
                st.info("Tip: If your resume is scanned, try uploading a text-based PDF or a DOCX file.")
                st.stop()
            st.session_state.profile = profile
            st.session_state.interview_state = interview_state
            st.session_state.interview_complete = False

    profile = st.session_state.profile
    interview_state = st.session_state.interview_state

    # ------------------ Initial Question ------------------
    if "current_question" not in st.session_state:
        st.session_state.current_question = cached_generate_question(
            interview_state.current_skill,
            interview_state.depth_level,
            interview_state.asked_questions
        )

    # ------------------ Skill Analysis ------------------
    with st.expander("📊 Skill Analysis"):
        for skill, info in profile.skills.items():
            st.write(f"**{skill}**")
            st.write(f"- Confidence: {info.confidence}")
            st.write(f"- Depth: {info.depth_estimate}")

    # ------------------ CHAT INTERVIEW ------------------
    st.header("🎤 Interactive Interview")

    # ---- Render Chat History ----
    for turn in interview_state.history:
        with st.chat_message("assistant"):
            st.write(turn["question"])
        st.chat_message("user").write(turn["answer"])

        with st.chat_message("assistant"):
            st.success(f"Verdict: {turn['quality']['quality']}")
            st.write(turn["quality"]["feedback"])

            concepts = turn["quality"].get("concepts")
            if concepts and concepts.get("missing"):
                st.warning("Missing concepts: " + ", ".join(concepts["missing"]))

    # ------------------ FINAL SUMMARY ------------------
    if st.session_state.interview_complete:
        st.divider()
        st.header("📋 Final Interview Summary")
        st.success("✅ Interview Completed")

        verdicts = []
        mentioned = []
        missing = []

        for turn in interview_state.history:
            verdicts.append(turn["quality"]["quality"])
            c = turn["quality"].get("concepts")
            if c:
                mentioned.extend(c.get("mentioned", []))
                missing.extend(c.get("missing", []))

        verdict_counts = Counter(verdicts)
        mentioned_counts = Counter(mentioned)
        missing_counts = Counter(missing)

        st.subheader("📊 Performance Breakdown")
        for k, v in verdict_counts.items():
            st.write(f"- **{k}**: {v}")

        if mentioned_counts:
            st.subheader("💪 Strong Concepts")
            for c, n in mentioned_counts.most_common(5):
                st.write(f"✔️ {c} ({n} times)")

        if missing_counts:
            st.subheader("❌ Missing / Weak Concepts")
            for c, n in missing_counts.most_common():
                st.write(f"⚠️ {c} ({n} times)")

        st.subheader("🏁 Final Verdict")
        if verdict_counts.get("Strong", 0) >= 2:
            st.success("Hire Recommendation: **Strong Yes**")
        elif verdict_counts.get("Strong", 0) == 1:
            st.warning("Hire Recommendation: **Borderline**")
        else:
            st.error("Hire Recommendation: **Needs Improvement**")

        st.stop()

    # ---- Current Question (Typing Effect) ----
    with st.chat_message("assistant"):
        typewriter(st.session_state.current_question)

    # ---- User Input ----
    answer = st.chat_input("Type your answer here...")

    if answer:

        with st.spinner("Evaluating your answer..."):
            evaluation = evaluate_answer(
                interview_state.current_skill,
                st.session_state.current_question,
                answer
            )

        quality = evaluation["quality"]

        # Record turn
        interview_state.record(
            st.session_state.current_question,
            answer,
            evaluation
        )

        # ---- Adaptive Termination Check ----
        if should_end_interview(interview_state.history):
            st.session_state.interview_complete = True
            st.rerun()

        # ---- Decide Next Depth ----
        interview_state.depth_level = decide_next_level(
            interview_state.depth_level,
            quality
        )

        # ---- Next Question ----
        st.session_state.current_question = cached_generate_question(
            interview_state.current_skill,
            interview_state.depth_level,
            interview_state.asked_questions
        )

        st.rerun()
