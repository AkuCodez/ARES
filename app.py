import streamlit as st
import tempfile
import os

from resume_engine.run_pipeline import run
from resume_engine.question_generator import generate_question
from resume_engine.answer_evaluator import evaluate_answer
from resume_engine.next_question_policy import decide_next_level

# ------------------ Page Setup ------------------
st.set_page_config(
    page_title="ARES – AI Interview Simulator",
    layout="wide"
)

st.title("🧠 ARES – AI Resume-Based Interview System")
st.caption("Upload a resume and experience a realistic AI-driven technical interview")

# ------------------ File Upload ------------------
uploaded_file = st.file_uploader(
    "Upload your Resume (PDF or DOCX)",
    type=["pdf", "docx"]
)

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.read())
        resume_path = tmp.name

    st.success("Resume uploaded successfully!")

    # ------------------ Run Resume Analysis ------------------
    with st.spinner("Analyzing resume and preparing interview..."):
        profile, interview_state = run(resume_path)

    # Store objects in session state (IMPORTANT)
    if "interview_state" not in st.session_state:
        st.session_state.interview_state = interview_state

    if "profile" not in st.session_state:
        st.session_state.profile = profile

    if "current_question" not in st.session_state:
        st.session_state.current_question = generate_question(
            interview_state.current_skill,
            interview_state.depth_level,
            interview_state.asked_questions
        )

    # ------------------ Skill Analysis ------------------
    st.header("📊 Skill Analysis")

    for skill, info in profile.skills.items():
        with st.expander(f"🔹 {skill}"):
            st.write(f"**Confidence:** {info.confidence}")
            st.write(f"**Depth:** {info.depth_estimate}")
            if info.evidence:
                st.write("**Evidence:**")
                for ev in info.evidence:
                    st.write(f"- {ev}")

    # ------------------ Resume Red Flags ------------------
    if profile.risk_flags:
        st.header("⚠️ Resume Red Flags")
        for flag in profile.risk_flags:
            st.warning(flag)

    # ------------------ Interactive Interview ------------------
    # ------------------ Interactive Interview ------------------
    st.header("🎤 Interactive Interview")

    st.subheader("Question")
    st.write(st.session_state.current_question)

    with st.form(key="answer_form", clear_on_submit=True):
        answer = st.text_area("Your Answer")
        submitted = st.form_submit_button("Submit Answer")

    if submitted:
        evaluation = evaluate_answer(
            st.session_state.interview_state.current_skill,
            st.session_state.current_question,
            answer
        )

        quality = evaluation["quality"]

    # Record interview turn
        st.session_state.interview_state.record(
            st.session_state.current_question,
            answer,
            evaluation
        )

    # ---- Feedback ----
        st.success(f"Verdict: {quality}")
        st.info(evaluation["feedback"])

    # ---- Concept Feedback ----
        concepts = evaluation.get("concepts")
        if concepts and concepts["coverage"] is not None:
            st.write(
                f"**Concept Coverage:** "
                f"{len(concepts['mentioned'])}/"
                f"{len(concepts['mentioned']) + len(concepts['missing'])}"
            )
            if concepts["missing"]:
                st.warning(
                    "Missing concepts: " + ", ".join(concepts["missing"])
                )

    # ---- Decide next depth ----
        st.session_state.interview_state.depth_level = decide_next_level(
            st.session_state.interview_state.depth_level,
            quality
        )

    # ---- Generate next question ----
        st.session_state.current_question = generate_question(
            st.session_state.interview_state.current_skill,
            st.session_state.interview_state.depth_level,
            st.session_state.interview_state.asked_questions
        )
        st.rerun()


    # ------------------ Interview History ------------------
    if st.session_state.interview_state.history:
        st.header("📝 Interview History")
        for i, turn in enumerate(st.session_state.interview_state.history, 1):
            st.subheader(f"Question {i}")
            st.write(f"**Q:** {turn['question']}")
            st.write(f"**A:** {turn['answer']}")
            st.write(f"**Verdict:** {turn['quality']['quality']}")
            st.write(f"**Feedback:** {turn['quality']['feedback']}")

    # Cleanup temp file
    os.remove(resume_path)
