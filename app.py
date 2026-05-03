import streamlit as st
import tempfile
import os
import time
from collections import Counter

from resume_engine.report import generate_report
from resume_engine.run_pipeline import run
from resume_engine.questions import generate_question, select_skill_for_question
from resume_engine.evaluator import evaluate_answer
from resume_engine.policy import decide_next_level
from resume_engine.models import InterviewState


# ------------------ CONFIG ------------------
MAX_QUESTIONS = 6          # hard cap
MIN_QUESTIONS = 3          # minimum before early stop
TYPE_DELAY = 0.03          # typing speed

# ------------------ Page Setup ------------------
st.set_page_config(
    page_title="ARES – AI Interview Simulator",
    layout="wide"
)

st.title("🧠 ARES – AI Resume-Based Interview System")
st.caption("Upload a resume and experience a realistic AI-driven technical interview")

# app.py — ADD after st.caption(...)

with st.expander("🎯 Optional: Paste a Job Description to tailor the interview"):
    jd_text = st.text_area(
        "Job Description",
        placeholder="Paste the JD here...",
        height=150,
        key="jd_input"
    )
    if jd_text and "jd_text" not in st.session_state:
        st.session_state.jd_text = jd_text
        st.success("✅ JD saved — interview will be tailored to this role")
        
# after JD expander block
# REPLACE entire persona block in app.py with:

if "persona" not in st.session_state:
    st.subheader("🎭 Choose Interviewer Style")
    persona_choice = st.selectbox(
        "Style",
        ["😊 Friendly", "🏢 FAANG", "🚀 Startup", "🎓 Academic"],
        key="persona_select"
    )
    if st.button("Confirm Style"):
        st.session_state.persona = persona_choice
        st.rerun()
    st.stop()   # ← blocks resume upload until persona is picked
else:
    st.info(f"🎭 Interviewer: **{st.session_state.persona}**")

# ------------------ TYPING EFFECT ------------------
def typewriter(text, delay=TYPE_DELAY):
    placeholder = st.empty()
    rendered = ""
    for word in text.split():
        rendered += word + " "
        placeholder.markdown(rendered)
        time.sleep(delay)

# ------------------ CACHED HELPERS ------------------
def cached_run(resume_bytes):
    suffix = ".docx" if uploaded_file.name.endswith(".docx") else ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(resume_bytes)
        path = tmp.name
    profile, interview_state = run(path)
    os.remove(path)
    return profile, interview_state


@st.cache_data(show_spinner=False)
def cached_generate_question(skill, depth, asked, profile=None, jd_text = None, persona = None):
    return generate_question(skill, depth, tuple(asked), profile, jd_text, persona)

# app.py — ADD this function near top with other helpers

def render_radar_chart(history):
    import plotly.graph_objects as go

    dims = ["correctness", "depth", "clarity"]
    scores = {d: [] for d in dims}

    for turn in history:
        s = turn.get("quality", {}).get("scores", {})
        for d in dims:
            if d in s:
                scores[d].append(s[d])

    avg = [
        (sum(scores[d]) / len(scores[d]) / 10) if scores[d] else 0
        for d in dims
    ]

    fig = go.Figure(go.Scatterpolar(
        r=avg + [avg[0]],
        theta=["Correctness", "Depth", "Clarity", "Correctness"],
        fill="toself",
        line_color="#7C3AED",
        fillcolor="rgba(124, 58, 237, 0.2)"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=40, b=40),
        height=350
    )
    st.plotly_chart(fig, use_container_width=True)
    
# ADD this function near render_radar_chart at top:

def render_confidence_timeline(history):
    import plotly.graph_objects as go

    _SCORE_MAP = {"strong": 1.0, "okay": 0.5, "weak": 0.0}
    turns  = list(range(1, len(history) + 1))
    scores = [_SCORE_MAP.get(t["quality"]["quality"].lower(), 0) for t in history]
    skills = [t.get("skill", "") for t in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=turns, y=scores,
        mode="lines+markers",
        line=dict(color="#7C3AED", width=3),
        marker=dict(size=10, color=scores, colorscale=[
            [0, "#DC2626"], [0.5, "#D97706"], [1, "#16A34A"]
        ]),
        text=[f"Q{i}: {s}" for i, s in zip(turns, skills)],
        hovertemplate="%{text}<br>Score: %{y}<extra></extra>"
    ))
    fig.update_layout(
        xaxis=dict(title="Question #", tickvals=turns),
        yaxis=dict(
            title="Performance",
            tickvals=[0, 0.5, 1.0],
            ticktext=["Weak", "Okay", "Strong"],
            range=[-0.1, 1.1]
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=20, b=40),
        height=300
    )
    st.plotly_chart(fig, use_container_width=True)

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

    verdicts = [turn["quality"]["quality"].lower() for turn in history]

    # ---- Rule 2: Two strong answers in a row ----
    if n >= 2 and verdicts[-1] == "strong" and verdicts[-2] == "strong":
        return True

    # ---- Rule 3: Repeated missing concepts ----
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
                profile, interview_state = cached_run(
                    uploaded_file.getvalue())
            except ValueError as e:
                st.error(str(e))
                st.info("Tip: If your resume is scanned, try uploading a text-based PDF or a DOCX file.")
                st.stop()
            st.cache_data.clear()
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
            interview_state.asked_questions,
            profile,
            st.session_state.get("jd_text"),
            st.session_state.get("persona")
        )

    # ------------------ Skill Analysis ------------------
    with st.expander("📊 Skill Analysis"):
        for skill, info in profile.skills.items():
            st.write(f"**{skill}**")
            st.write(f"- Confidence: {info.get('confidence', 0)}")
            st.write(f"- Depth: {info.get('depth_estimate', 'N/A')}")

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
            
        st.subheader("🕸️ Skill Radar")
        render_radar_chart(interview_state.history)
        
        st.subheader("📈 Confidence Timeline")
        render_confidence_timeline(interview_state.history)

        if mentioned_counts:
            st.subheader("💪 Strong Concepts")
            for c, n in mentioned_counts.most_common(5):
                st.write(f"✔️ {c} ({n} times)")

        if missing_counts:
            st.subheader("❌ Missing / Weak Concepts")
            for c, n in missing_counts.most_common():
                st.write(f"⚠️ {c} ({n} times)")

        st.subheader("🏁 Final Verdict")
        
        if verdict_counts.get("strong", 0) >= 2:
            st.success("Hire Recommendation: **Strong Yes**")
        elif verdict_counts.get("strong", 0) == 1:
            st.warning("Hire Recommendation: **Borderline**")
        else:
            st.error("Hire Recommendation: **Needs Improvement**")
            
        st.divider()
        pdf_bytes = generate_report(profile, interview_state)
        st.download_button(
            label="📄 Download Interview Report (PDF)",
            data=pdf_bytes,
            file_name="ARES_Interview_Report.pdf",
            mime="application/pdf"
        )
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
        
        questions_on_skill = sum(
            1 for t in interview_state.history
            if t.get("skill") == interview_state.current_skill
        )
        if questions_on_skill >= 2 and len(interview_state.skill_queue) > 1:
            interview_state.advance_skill()

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

        missing = evaluation.get("concepts", {}).get("missing", [])
        followup = None

        if missing and quality != "strong":
            from resume_engine.questions import generate_followup
            followup = generate_followup(
                interview_state.current_skill,
                missing,
                answer
            )

        st.session_state.current_question = followup or cached_generate_question(
            interview_state.current_skill,
            interview_state.depth_level,
            interview_state.asked_questions,
            profile,
            st.session_state.get("jd_text"),
            st.session_state.get("persona")
        )

        st.rerun()
