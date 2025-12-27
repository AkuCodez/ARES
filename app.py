import streamlit as st
import tempfile
import os
from collections import Counter

from resume_engine.run_pipeline import run
from resume_engine.question_generator import generate_question
from resume_engine.answer_evaluator import evaluate_answer
from resume_engine.next_question_policy import decide_next_level

# ------------------ CONFIG ------------------
MAX_QUESTIONS = 3

# ------------------ Page Setup ------------------
st.set_page_config(
    page_title="ARES – AI Interview Simulator",
    layout="wide"
)

st.title("🧠 ARES – AI Resume-Based Interview System")
st.caption("Upload a resume and experience a realistic AI-driven technical interview")

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


# ------------------ File Upload ------------------
uploaded_file = st.file_uploader(
    "Upload your Resume (PDF or DOCX)",
    type=["pdf", "docx"]
)

if uploaded_file:

    # ------------------ Resume Analysis ------------------
    if "profile" not in st.session_state:
        with st.spinner("Analyzing resume and preparing interview..."):
            profile, interview_state = cached_run(uploaded_file.getvalue())
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
    st.header("📊 Skill Analysis")
    for skill, info in profile.skills.items():
        with st.expander(f"🔹 {skill}"):
            st.write(f"**Confidence:** {info.confidence}")
            st.write(f"**Depth:** {info.depth_estimate}")

    # ------------------ Interactive Interview ------------------
    st.header("🎤 Interactive Interview")

    if not st.session_state.interview_complete:

        with st.form(key="answer_form", clear_on_submit=True):
            st.subheader(f"Question {len(interview_state.history) + 1}")
            st.write(st.session_state.current_question)

            answer = st.text_area("Your Answer")
            submitted = st.form_submit_button("Submit Answer")

        if submitted and answer.strip():

            with st.spinner("Evaluating your answer..."):
                evaluation = evaluate_answer(
                    interview_state.current_skill,
                    st.session_state.current_question,
                    answer
                )

            quality = evaluation["quality"]

            # ---- Record Turn ----
            interview_state.record(
                st.session_state.current_question,
                answer,
                evaluation
            )

            # ---- Immediate Feedback ----
            st.success(f"Verdict: {quality}")
            st.info(evaluation["feedback"])

            # ---- Concept Feedback ----
            concepts = evaluation.get("concepts")
            if concepts and concepts.get("coverage") is not None:
                st.write(
                    f"**Concept Coverage:** "
                    f"{len(concepts['mentioned'])}/"
                    f"{len(concepts['mentioned']) + len(concepts['missing'])}"
                )
                if concepts["missing"]:
                    st.warning(
                        "Missing concepts: " + ", ".join(concepts["missing"])
                    )

            # ---- Stop Interview if Limit Reached ----
            if len(interview_state.history) >= MAX_QUESTIONS:
                st.session_state.interview_complete = True
                st.rerun()

            # ---- Decide Next Depth ----
            interview_state.depth_level = decide_next_level(
                interview_state.depth_level,
                quality
            )

            # ---- Generate Next Question ----
            st.session_state.current_question = cached_generate_question(
                interview_state.current_skill,
                interview_state.depth_level,
                interview_state.asked_questions
            )

            st.rerun()

    # ------------------ Interview History (ALWAYS SHOWN) ------------------
    if interview_state.history:
        st.header("📝 Interview History")
        for i, turn in enumerate(interview_state.history, 1):
            st.subheader(f"Question {i}")
            st.write(f"**Q:** {turn['question']}")
            st.write(f"**A:** {turn['answer']}")
            st.write(f"**Verdict:** {turn['quality']['quality']}")
            st.write(f"**Feedback:** {turn['quality']['feedback']}")

    # ------------------ FINAL DETAILED SUMMARY ------------------
    if st.session_state.interview_complete:
        st.header("📋 Final Interview Summary")
        st.success("✅ Interview Completed")

        verdicts = []
        missing_concepts = []
        mentioned_concepts = []

        for turn in interview_state.history:
            verdicts.append(turn["quality"]["quality"])
            concepts = turn["quality"].get("concepts")
            if concepts:
                mentioned_concepts.extend(concepts.get("mentioned", []))
                missing_concepts.extend(concepts.get("missing", []))

        verdict_counts = Counter(verdicts)
        missing_counter = Counter(missing_concepts)
        mentioned_counter = Counter(mentioned_concepts)

        # ---- Overall Performance ----
        st.subheader("📊 Overall Performance")
        for k, v in verdict_counts.items():
            st.write(f"- **{k}**: {v}")

        # ---- Strengths ----
        if mentioned_counter:
            st.subheader("💪 Strong Concepts")
            for concept, freq in mentioned_counter.most_common(5):
                st.write(f"✔️ {concept} (mentioned {freq} times)")

        # ---- Weak Areas ----
        if missing_counter:
            st.subheader("❌ Missing / Weak Concepts")
            for concept, freq in missing_counter.most_common():
                st.write(f"⚠️ {concept} (missed {freq} times)")

        # ---- Final Verdict ----
        st.subheader("🏁 Final Verdict")
        if verdict_counts.get("Strong", 0) >= 2:
            st.success("Hire Recommendation: **Strong Yes**")
        elif verdict_counts.get("Strong", 0) == 1:
            st.warning("Hire Recommendation: **Borderline**")
        else:
            st.error("Hire Recommendation: **Needs Improvement**")

        st.info("This summary is generated from concept-level interview analysis.")
