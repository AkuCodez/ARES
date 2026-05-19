import streamlit as st
import tempfile
import os
import time
from collections import Counter

from resume_engine.report import generate_report
from resume_engine.run_pipeline import run
from resume_engine.questions import generate_question, select_skill_for_question, generate_hint
from resume_engine.evaluator import evaluate_answer, apply_hint_penalty
from resume_engine.policy import decide_next_level
from resume_engine.models import InterviewState
from resume_engine.anticheat import detect_cheating
from resume_engine.skill_gaps import generate_skill_gaps
from resume_engine.sharecard import save_result, fetch_result

# ── CONFIG ────────────────────────────────────────────────────────────────
MAX_QUESTIONS = 6
MIN_QUESTIONS = 3
TYPE_DELAY    = 0.025

# ── PAGE CONFIG ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ARES – AI Interview Simulator",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CUSTOM CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Syne', sans-serif !important;
    background-color: #0A0A0F !important;
    color: #E2E8F0 !important;
}

/* ── Hide streamlit chrome ── */
#MainMenu, footer { visibility: hidden; }
[data-testid="stSidebarCollapseButton"] { visibility: visible !important; }.block-container { padding-top: 2rem !important; max-width: 1100px !important; }

/* ── Hero header ── */
.ares-header {
    text-align: center;
    padding: 2.5rem 0 1.5rem;
    border-bottom: 1px solid #1E1E2E;
    margin-bottom: 2rem;
}
.ares-header h1 {
    font-size: 3rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    background: linear-gradient(135deg, #A78BFA 0%, #60A5FA 50%, #34D399 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    line-height: 1.1;
}
.ares-header p {
    color: #64748B;
    font-size: 0.95rem;
    margin-top: 0.5rem;
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: 0.02em;
}

/* ── Cards ── */
.ares-card {
    background: #0F0F1A;
    border: 1px solid #1E1E2E;
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.ares-card-accent {
    border-left: 3px solid #7C3AED;
}

/* ── Persona grid ── */
.persona-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin: 1.5rem 0;
}
.persona-card {
    background: #0F0F1A;
    border: 1px solid #1E1E2E;
    border-radius: 12px;
    padding: 1.2rem;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: center;
}
.persona-card:hover { border-color: #7C3AED; transform: translateY(-2px); }
.persona-card .icon { font-size: 2rem; margin-bottom: 0.4rem; }
.persona-card .name { font-weight: 700; font-size: 1rem; }
.persona-card .desc { color: #64748B; font-size: 0.8rem; margin-top: 0.2rem; }

/* ── Verdict badges ── */
.verdict-strong {
    display: inline-block;
    background: #064E3B;
    color: #34D399;
    border: 1px solid #065F46;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.8rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.verdict-okay {
    display: inline-block;
    background: #451A03;
    color: #FCD34D;
    border: 1px solid #78350F;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.8rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.verdict-weak {
    display: inline-block;
    background: #450A0A;
    color: #FCA5A5;
    border: 1px solid #7F1D1D;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.8rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* ── Skill chip ── */
.skill-chip {
    display: inline-block;
    background: #1E1E2E;
    border: 1px solid #2D2D3E;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.8rem;
    color: #A78BFA;
    font-family: 'JetBrains Mono', monospace !important;
    margin: 2px;
}

/* ── Section titles ── */
.section-title {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #475569;
    margin-bottom: 1rem;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Metric cards ── */
.metric-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 1.5rem;
}
.metric-card {
    background: #0F0F1A;
    border: 1px solid #1E1E2E;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}
.metric-card .metric-val {
    font-size: 2rem;
    font-weight: 800;
    color: #A78BFA;
    line-height: 1;
}
.metric-card .metric-label {
    font-size: 0.75rem;
    color: #64748B;
    margin-top: 0.3rem;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Hire verdict ── */
.hire-strong  { background:#064E3B; color:#34D399; border:1px solid #065F46; border-radius:12px; padding:1rem 1.5rem; text-align:center; font-size:1.3rem; font-weight:800; }
.hire-border  { background:#451A03; color:#FCD34D; border:1px solid #78350F; border-radius:12px; padding:1rem 1.5rem; text-align:center; font-size:1.3rem; font-weight:800; }
.hire-no      { background:#450A0A; color:#FCA5A5; border:1px solid #7F1D1D; border-radius:12px; padding:1rem 1.5rem; text-align:center; font-size:1.3rem; font-weight:800; }

/* ── Gap priority ── */
.gap-high   { border-left: 3px solid #EF4444 !important; }
.gap-medium { border-left: 3px solid #F59E0B !important; }
.gap-low    { border-left: 3px solid #10B981 !important; }

/* ── Chat messages override ── */
[data-testid="stChatMessage"] {
    background: #0F0F1A !important;
    border: 1px solid #1E1E2E !important;
    border-radius: 12px !important;
    margin-bottom: 0.5rem !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #1E1E2E !important;
    color: #A78BFA !important;
    border: 1px solid #2D2D3E !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #7C3AED !important;
    color: white !important;
    border-color: #7C3AED !important;
}

/* ── Primary confirm button ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7C3AED, #4F46E5) !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #0F0F1A !important;
    border: 2px dashed #2D2D3E !important;
    border-radius: 12px !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #0F0F1A !important;
    border: 1px solid #1E1E2E !important;
    border-radius: 12px !important;
}

/* ── Progress bar ── */
.stProgress > div > div {
    background: linear-gradient(90deg, #7C3AED, #60A5FA) !important;
    border-radius: 4px !important;
}

/* ── Info/warning/success boxes ── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-left-width: 3px !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: #0F0F1A !important;
    border: 1px solid #2D2D3E !important;
    border-radius: 8px !important;
    color: #E2E8F0 !important;
}

/* ── Divider ── */
hr { border-color: #1E1E2E !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: #7C3AED !important; }

/* ── Interview turn number badge ── */
.turn-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #475569;
    margin-bottom: 0.3rem;
}
</style>
""", unsafe_allow_html=True)

# ── HERO HEADER ───────────────────────────────────────────────────────────
st.markdown("""
<div class="ares-header">
    <h1>ARES</h1>
    <p>AI Resume-Based Interview System · powered by Groq llama-3.3-70b</p>
</div>
""", unsafe_allow_html=True)

# ── SHARED RESULT VIEW (read-only) ────────────────────────────────────────
try:
    _result_id = st.query_params["result"]
except (KeyError, AttributeError, Exception):
    _result_id = None

if _result_id:
    data = fetch_result(_result_id)
    if data:
        st.markdown("### 📊 Shared Interview Result")
        
        # Verdict counts
        vc = data.get("verdict_counts", {})
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("✅ Strong", vc.get("strong", 0))
        with col2: st.metric("~ Okay",   vc.get("okay", 0))
        with col3: st.metric("✗ Weak",   vc.get("weak", 0))

        st.divider()

        # Skills tested
        skills = data.get("skills", [])
        st.markdown('<div class="section-title">Skills Tested</div>', unsafe_allow_html=True)
        st.markdown("".join(f'<span class="skill-chip">{s}</span>' for s in skills),
                    unsafe_allow_html=True)

        st.divider()

        # Q&A review
        st.markdown('<div class="section-title">Answer Review</div>', unsafe_allow_html=True)
        for i, turn in enumerate(data.get("history", []), 1):
            q = turn.get("quality", {})
            v = q.get("quality", "weak").lower()
            color = {"strong":"#34D399","okay":"#FCD34D","weak":"#FCA5A5"}.get(v,"#94A3B8")
            with st.expander(f"Q{i} · {turn.get('skill','')} — {v.upper()}"):
                st.markdown(f"**Question:** {turn['question']}")
                st.markdown(f"**Answer:** {turn['answer']}")
                st.markdown(f'<div style="color:{color}">{q.get("feedback","")}</div>',
                            unsafe_allow_html=True)
                scores = q.get("scores", {})
                if scores:
                    c1,c2,c3 = st.columns(3)
                    with c1: st.metric("Correctness", f"{scores.get('correctness',0)}/10")
                    with c2: st.metric("Depth",       f"{scores.get('depth',0)}/10")
                    with c3: st.metric("Clarity",     f"{scores.get('clarity',0)}/10")

        # Gaps
        gaps = data.get("gaps", [])
        if gaps:
            st.divider()
            st.markdown('<div class="section-title">Study Recommendations</div>',
                        unsafe_allow_html=True)
            for gap in gaps:
                p = gap.get("priority","medium")
                with st.expander(f"{gap['topic']} — {p.upper()}"):
                    st.markdown(f"**Why:** {gap.get('reason','')}")
                    st.markdown(f"**Focus:** {gap.get('what_to_learn','')}")
                    st.markdown(f"📖 [{gap.get('resource_name','')}]({gap.get('resource_url','#')})")
    else:
        st.error(f"Result not found: `{_result_id}`")
    st.stop()

# ── HELPERS ───────────────────────────────────────────────────────────────

def typewriter(text, delay=TYPE_DELAY):
    placeholder = st.empty()
    rendered = ""
    for word in text.split():
        rendered += word + " "
        placeholder.markdown(rendered)
        time.sleep(delay)


def verdict_badge(verdict: str) -> str:
    v = verdict.lower()
    css = {"strong": "verdict-strong", "okay": "verdict-okay", "weak": "verdict-weak"}
    return f'<span class="{css.get(v, "verdict-okay")}">{v}</span>'


def cached_run(resume_bytes, filename):
    suffix = ".docx" if filename.endswith(".docx") else ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(resume_bytes)
        path = tmp.name
    profile, interview_state = run(path)
    os.remove(path)
    return profile, interview_state


@st.cache_data(show_spinner=False)
def cached_generate_question(skill, depth, asked, profile=None, jd_text=None, persona=None):
    return generate_question(skill, depth, tuple(asked), profile, jd_text, persona)


def render_radar_chart(history):
    import plotly.graph_objects as go
    dims   = ["correctness", "depth", "clarity"]
    scores = {d: [] for d in dims}
    for turn in history:
        s = turn.get("quality", {}).get("scores", {})
        for d in dims:
            if d in s: scores[d].append(s[d])
    avg = [(sum(scores[d]) / len(scores[d]) / 10) if scores[d] else 0 for d in dims]
    fig = go.Figure(go.Scatterpolar(
        r=avg + [avg[0]],
        theta=["Correctness", "Depth", "Clarity", "Correctness"],
        fill="toself",
        line=dict(color="#A78BFA", width=2),
        fillcolor="rgba(124,58,237,0.15)"
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="#0F0F1A",
            radialaxis=dict(visible=True, range=[0,1], gridcolor="#1E1E2E", color="#475569"),
            angularaxis=dict(gridcolor="#1E1E2E", color="#94A3B8")
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40,r=40,t=20,b=20),
        height=300
    )
    st.plotly_chart(fig, use_container_width=True)


def render_confidence_timeline(history):
    import plotly.graph_objects as go
    _MAP   = {"strong": 1.0, "okay": 0.5, "weak": 0.0}
    turns  = list(range(1, len(history)+1))
    scores = [_MAP.get(t["quality"]["quality"].lower(), 0) for t in history]
    skills = [t.get("skill","") for t in history]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=turns, y=scores,
        mode="lines+markers",
        line=dict(color="#A78BFA", width=2),
        marker=dict(size=10, color=scores,
            colorscale=[[0,"#EF4444"],[0.5,"#F59E0B"],[1,"#10B981"]],
            line=dict(color="#0A0A0F", width=2)
        ),
        text=[f"Q{i}: {s}" for i,s in zip(turns,skills)],
        hovertemplate="%{text}<br>Score: %{y}<extra></extra>"
    ))
    fig.update_layout(
        xaxis=dict(title="Question", tickvals=turns, gridcolor="#1E1E2E", color="#475569"),
        yaxis=dict(title="", tickvals=[0,0.5,1.0],
            ticktext=["Weak","Okay","Strong"],
            range=[-0.1,1.1], gridcolor="#1E1E2E", color="#475569"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60,r=20,t=10,b=40),
        height=250,
        font=dict(family="JetBrains Mono", color="#94A3B8")
    )
    st.plotly_chart(fig, use_container_width=True)


def should_end_interview(history):
    n = len(history)
    if n < MIN_QUESTIONS: return False
    if n >= MAX_QUESTIONS: return True
    verdicts = [t["quality"]["quality"].lower() for t in history]
    if n >= 2 and verdicts[-1] == "strong" and verdicts[-2] == "strong": return True
    missing  = []
    for turn in history:
        c = turn["quality"].get("concepts")
        if c: missing.extend(c.get("missing", []))
    if any(f >= 2 for f in Counter(missing).values()): return True
    return False


# ── JD EXPANDER ───────────────────────────────────────────────────────────
with st.expander("🎯 Paste a Job Description to tailor the interview (optional)"):
    jd_text = st.text_area("Job Description", placeholder="Paste JD here...",
                           height=120, key="jd_input")
    if jd_text and "jd_text" not in st.session_state:
        st.session_state.jd_text = jd_text
        st.success("✅ JD saved — questions will be tailored to this role")


# ── PERSONA PICKER ────────────────────────────────────────────────────────
# REPLACE the entire persona picker section with:

if "persona" not in st.session_state:
    st.markdown('<div class="section-title">Choose your interviewer</div>', unsafe_allow_html=True)
    
    persona_choice = st.radio(
        "",
        ["😊 Friendly", "🏢 FAANG", "🚀 Startup", "🎓 Academic"],
        captions=[
            "Warm, supportive, hints available",
            "Rigorous, deep, no hand-holding", 
            "Fast, broad, shipping focused",
            "Theory, first principles, complexity"
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="persona_select"
    )
    
    if st.button("Begin Interview →", type="primary"):
        st.session_state.persona = persona_choice
        st.rerun()
    st.stop()

# ── PERSONA BADGE ─────────────────────────────────────────────────────────
col_p, col_s = st.columns([1, 3])
with col_p:
    st.markdown(f'<span class="skill-chip">{st.session_state.persona}</span>',
                unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-title">Session</div>', unsafe_allow_html=True)
    st.markdown(f'<span class="skill-chip">{st.session_state.persona}</span><br><br>',
                unsafe_allow_html=True)

    if "profile" in st.session_state and "interview_state" in st.session_state:
        _state = st.session_state.interview_state
        _turn  = len(_state.history)

        st.markdown('<div class="section-title">Progress</div>', unsafe_allow_html=True)
        st.progress(min(_turn / MAX_QUESTIONS, 1.0),
                    text=f"{_turn}/{MAX_QUESTIONS} questions")

        st.markdown('<div class="section-title" style="margin-top:1rem;">Current Skill</div>',
                    unsafe_allow_html=True)
        st.markdown(
            f'<span class="skill-chip" style="color:#A78BFA;border-color:#7C3AED;">'
            f'{_state.current_skill}</span>'
            f'<div style="font-size:0.7rem;color:#475569;margin-top:0.4rem;">'
            f'Depth {_state.depth_level}/3</div>',
            unsafe_allow_html=True)

        st.markdown('<div class="section-title" style="margin-top:1rem;">Skill Queue</div>',
                    unsafe_allow_html=True)
        for s in _state.skill_queue:
            active = s == _state.current_skill
            style  = "color:#A78BFA;border-color:#7C3AED;" if active else ""
            st.markdown(f'<span class="skill-chip" style="{style}">{s}</span>',
                        unsafe_allow_html=True)

        if _turn > 0:
            vc = _state.verdict_counts
            st.markdown('<div class="section-title" style="margin-top:1rem;">Score</div>',
                        unsafe_allow_html=True)
            st.markdown(f"""
            <div class="ares-card" style="padding:0.75rem;">
                <div style="font-size:0.75rem;display:flex;flex-direction:column;gap:4px;">
                    <span style="color:#34D399;">✓ {vc.get('strong',0)} strong</span>
                    <span style="color:#FCD34D;">~ {vc.get('okay',0)} okay</span>
                    <span style="color:#FCA5A5;">✗ {vc.get('weak',0)} weak</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Session</div>', unsafe_allow_html=True)
        if st.button("↺ Restart Interview", use_container_width=True):
            for key in ["profile","interview_state","current_question",
                        "current_hint","hint_used","interview_complete",
                        "voice_transcript","last_audio_hash","transcribe_error",
                        "input_mode","recording","jd_text"]:
                st.session_state.pop(key, None)
            st.rerun()

# ── FILE UPLOAD ───────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Upload Resume</div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("", type=["pdf","docx"], label_visibility="collapsed")

if uploaded_file:

    # ── RESUME ANALYSIS ───────────────────────────────────────────────────
    if "profile" not in st.session_state:
        with st.spinner("Analyzing resume..."):
            try:
                profile, interview_state = cached_run(
                    uploaded_file.getvalue(), uploaded_file.name)
            except ValueError as e:
                st.error(str(e))
                st.stop()
        st.cache_data.clear()
        st.session_state.profile           = profile
        st.session_state.interview_state   = interview_state
        st.session_state.interview_complete = False

    profile         = st.session_state.profile
    interview_state = st.session_state.interview_state

    # ── INITIAL QUESTION ──────────────────────────────────────────────────
    if "current_question" not in st.session_state:
        st.session_state.current_question = cached_generate_question(
            interview_state.current_skill,
            interview_state.depth_level,
            interview_state.asked_questions,
            profile,
            st.session_state.get("jd_text"),
            st.session_state.get("persona")
        )

    # ── SKILL ANALYSIS EXPANDER ───────────────────────────────────────────
    with st.expander("📊 Skill Analysis", expanded=False):
        chips = "".join(
            f'<span class="skill-chip">{s}</span>'
            for s in profile.skills.keys()
        )
        st.markdown(chips, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        for skill, info in profile.skills.items():
            info_d = info if isinstance(info, dict) else vars(info)
            conf   = info_d.get("confidence", 0)
            depth  = info_d.get("depth_estimate", "N/A")
            col1, col2, col3 = st.columns([2,1,1])
            with col1: st.write(f"**{skill}**")
            with col2: st.caption(depth)
            with col3: st.progress(float(conf), text=f"{float(conf):.0%}")

    # ── FINAL SUMMARY ─────────────────────────────────────────────────────
    if st.session_state.interview_complete:
        st.divider()
        st.markdown('<div class="section-title">Interview Complete</div>', unsafe_allow_html=True)

        history       = interview_state.history
        verdicts      = [t["quality"]["quality"].lower() for t in history]
        verdict_counts = Counter(verdicts)
        total          = len(history)
        strong_n       = verdict_counts.get("strong", 0)
        score          = sum({"strong":1.0,"okay":0.5,"weak":0.0}.get(v,0) for v in verdicts) / max(total,1)

        # ── Metric row ────────────────────────────────────────────────────
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-val">{total}</div>
                <div class="metric-label">Questions</div>
            </div>
            <div class="metric-card">
                <div class="metric-val">{score:.0%}</div>
                <div class="metric-label">Overall Score</div>
            </div>
            <div class="metric-card">
                <div class="metric-val">{strong_n}</div>
                <div class="metric-label">Strong Answers</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Hire verdict ──────────────────────────────────────────────────
        if strong_n >= 2:
            st.markdown('<div class="hire-strong">✅ Hire Recommendation: Strong Yes</div>',
                        unsafe_allow_html=True)
        elif strong_n == 1:
            st.markdown('<div class="hire-border">⚡ Hire Recommendation: Borderline</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div class="hire-no">❌ Hire Recommendation: Needs Improvement</div>',
                        unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Charts side by side ───────────────────────────────────────────
        col_r, col_t = st.columns(2)
        with col_r:
            st.markdown('<div class="section-title">Skill Radar</div>', unsafe_allow_html=True)
            render_radar_chart(history)
        with col_t:
            st.markdown('<div class="section-title">Confidence Timeline</div>', unsafe_allow_html=True)
            render_confidence_timeline(history)

        # ── Concepts ──────────────────────────────────────────────────────
        mentioned, missing_list = [], []
        for turn in history:
            c = turn["quality"].get("concepts")
            if c:
                mentioned.extend(c.get("mentioned", []))
                missing_list.extend(c.get("missing", []))

        col_m, col_w = st.columns(2)
        with col_m:
            st.markdown('<div class="section-title">💪 Strong Concepts</div>', unsafe_allow_html=True)
            for c, n in Counter(mentioned).most_common(5):
                st.markdown(f'<span class="skill-chip">✓ {c}</span>', unsafe_allow_html=True)
        with col_w:
            st.markdown('<div class="section-title">❌ Gaps</div>', unsafe_allow_html=True)
            for c, n in Counter(missing_list).most_common(5):
                st.markdown(f'<span class="skill-chip" style="color:#FCA5A5;border-color:#7F1D1D">⚠ {c}</span>',
                            unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Q&A Review ────────────────────────────────────────────────────
        st.markdown('<div class="section-title">Answer Review</div>',
                    unsafe_allow_html=True)
        for i, turn in enumerate(history, 1):
            q = turn["quality"]
            v = q["quality"].lower()
            color = {"strong":"#34D399","okay":"#FCD34D","weak":"#FCA5A5"}.get(v,"#94A3B8")
            with st.expander(
                f"Q{i} · {turn.get('skill','')} — {v.upper()}",
                expanded=False
            ):
                st.markdown(f"**Question:** {turn['question']}")
                st.markdown(f"**Your Answer:** {turn['answer']}")
                st.markdown(
                    f'<div style="font-size:0.82rem;color:{color}; margin-top:0.4rem;">'
                    f'{q["feedback"]}</div>',
                    unsafe_allow_html=True)
                scores = q.get("scores", {})
                if scores:
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric("Correctness", f"{scores.get('correctness',0)}/10")
                    with c2: st.metric("Depth",       f"{scores.get('depth',0)}/10")
                    with c3: st.metric("Clarity",     f"{scores.get('clarity',0)}/10")
                concepts = q.get("concepts", {})
                if concepts.get("mentioned"):
                    st.caption("✓ Covered: " + ", ".join(concepts["mentioned"]))
                if concepts.get("missing"):
                    st.caption("✗ Missed: " + ", ".join(concepts["missing"]))

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Study recommendations ─────────────────────────────────────────
        st.markdown('<div class="section-title">📚 Personalized Study Plan</div>',
                    unsafe_allow_html=True)
        with st.spinner("Generating recommendations..."):
            gaps = generate_skill_gaps(history, vars(profile))
        interview_state.gaps = gaps

        # ── SHAREABLE LINK ────────────────────────────────────────────────────────
        if "share_uuid" not in st.session_state:
            with st.spinner("Saving result..."):
                uuid = save_result(profile, interview_state, gaps)
                st.session_state.share_uuid = uuid

        share_url = f"https://ares-interview-prep.streamlit.app//?result={st.session_state.share_uuid}"
        st.markdown(f"🔗 **Shareable link:** [`{share_url}`]({share_url})")
        st.code(share_url)
        
        _PRIORITY_CONFIG = {
            "high":   ("🔴 High Priority",   "gap-high"),
            "medium": ("🟡 Medium Priority", "gap-medium"),
            "low":    ("🟢 Nice to Have",    "gap-low"),
        }
        for gap in gaps:
            priority      = gap.get("priority", "medium")
            label, css    = _PRIORITY_CONFIG.get(priority, _PRIORITY_CONFIG["medium"])
            bar_val       = {"high":1.0,"medium":0.6,"low":0.3}.get(priority, 0.5)
            resource_name = gap.get("resource_name", "Resource")
            resource_url  = gap.get("resource_url", "#")

            with st.expander(f"{label} — {gap['topic']}", expanded=(priority=="high")):
                c1, c2 = st.columns([3,1])
                with c1:
                    st.markdown(f"**Why:** {gap.get('reason','')}")
                    st.markdown(f"**Focus on:** {gap.get('what_to_learn','')}")
                    st.caption(gap.get("priority_reason",""))
                with c2:
                    st.metric("Est. time", gap.get("estimated_time","?"))
                st.markdown(f"📖 **[{resource_name}]({resource_url})**")
                st.progress(bar_val, text=f"Career impact: {label}")

        st.divider()

        # ── PDF download ──────────────────────────────────────────────────
        pdf_bytes = generate_report(profile, interview_state)
        st.download_button(
            "📄 Download Full Interview Report (PDF)",
            data=pdf_bytes,
            file_name="ARES_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        st.stop()

    # ── CHAT INTERVIEW ────────────────────────────────────────────────────
    st.markdown('<div class="section-title">🎤 Interview</div>', unsafe_allow_html=True)

    # Render history
    for i, turn in enumerate(interview_state.history, 1):
        with st.chat_message("assistant"):
            st.markdown(f'<div class="turn-badge">Q{i} · {turn.get("skill","")} · depth {turn.get("depth","")}</div>',
                        unsafe_allow_html=True)
            st.write(turn["question"])
        st.chat_message("user").write(turn["answer"])
        with st.chat_message("assistant"):
            st.markdown(verdict_badge(turn["quality"]["quality"]), unsafe_allow_html=True)
            st.caption(turn["quality"]["feedback"])
            concepts = turn["quality"].get("concepts")
            if concepts and concepts.get("missing"):
                st.caption("Missing: " + ", ".join(concepts["missing"]))
            cheat = turn["quality"].get("cheat_flags")
            if cheat and cheat["risk"] != "low":
                st.caption(f"⚠️ {cheat['risk'].upper()} authenticity risk: {', '.join(cheat['flags'])}")

    # Current question
    with st.chat_message("assistant"):
        st.markdown(
            f'<div class="turn-badge">Q{len(interview_state.history)+1} · '
            f'{interview_state.current_skill} · depth {interview_state.depth_level}</div>',
            unsafe_allow_html=True
        )
        typewriter(st.session_state.current_question)

    # Hint
    if st.button(f"💡 Request Hint", key=f"hint_{interview_state.turn}"):
        hint = generate_hint(interview_state.current_skill, st.session_state.current_question)
        st.session_state.hint_used    = True
        st.session_state.current_hint = hint

    if st.session_state.get("current_hint"):
        st.info(f"💡 {st.session_state.current_hint}")

    # ── INPUT MODE SELECTOR ───────────────────────────────────────────────
    st.markdown("""
    <style>
    .mode-bar { display:flex; gap:8px; margin-bottom:1rem; }
    .mode-btn {
        flex:1; padding:0.6rem 1rem; border-radius:10px; cursor:pointer;
        font-family:'JetBrains Mono',monospace; font-size:0.8rem; font-weight:600;
        text-align:center; border:1px solid #2D2D3E; transition:all 0.2s;
        background:#0F0F1A; color:#475569;
    }
    .mode-btn.active { background:#1E1E2E; color:#A78BFA; border-color:#7C3AED; }
    </style>
    """, unsafe_allow_html=True)

    if "input_mode" not in st.session_state:
        st.session_state.input_mode = "text"

    col_tm, col_vm, col_sp = st.columns([1, 1, 5])
    with col_tm:
        if st.button("⌨️  Text Mode",
                     type="primary" if st.session_state.input_mode == "text" else "secondary",
                     use_container_width=True, key="btn_textmode"):
            st.session_state.input_mode = "text"
            st.session_state.voice_transcript = ""
            st.rerun()
    with col_vm:
        if st.button("🎤  Voice Mode",
                     type="primary" if st.session_state.input_mode == "voice" else "secondary",
                     use_container_width=True, key="btn_voicemode"):
            st.session_state.input_mode = "voice"
            st.rerun()

    answer = None

    # ── TEXT MODE ─────────────────────────────────────────────────────────
    if st.session_state.input_mode == "text":
        answer = st.chat_input("Your answer...")

    # ── VOICE MODE ────────────────────────────────────────────────────────
    else:
        from audio_recorder_streamlit import audio_recorder
        from groq import Groq

        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        st.markdown("""
        <div class="ares-card" style="text-align:center; padding:2rem 1rem;">
            <div style="color:#475569; font-size:0.75rem; font-family:'JetBrains Mono',monospace;
                        text-transform:uppercase; letter-spacing:0.12em; margin-bottom:1.2rem;">
                Click mic to start · click again to stop
            </div>
        """, unsafe_allow_html=True)

        audio_bytes = audio_recorder(
            text="",
            recording_color="#7C3AED",
            neutral_color="#334155",
            icon_size="3x",
            pause_threshold=120.0,          # ← won't auto-stop for 2 mins
            sample_rate=16000,
            key=f"recorder_{interview_state.turn}"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Show persistent transcription errors
        if st.session_state.get("transcribe_error"):
            st.error(st.session_state.transcribe_error)

        # Only transcribe fresh audio (use hash to detect new recording)
        if audio_bytes:
            audio_hash = hash(audio_bytes)
            if audio_hash != st.session_state.get("last_audio_hash"):
                st.session_state.last_audio_hash = audio_hash
                st.session_state.transcribe_error = None
                with st.spinner("Transcribing..."):
                    try:
                        result = groq_client.audio.transcriptions.create(
                            file=("recording.wav", audio_bytes),
                            model="whisper-large-v3",
                            response_format="text"
                        )
                        st.session_state.voice_transcript = str(result).strip()
                        st.rerun()
                    except Exception as e:
                        st.session_state.transcribe_error = f"Transcription failed: {e}"
                        st.rerun()

        if st.session_state.get("voice_transcript"):
            st.markdown('<div class="section-title">📝 Transcript — review before submitting</div>',
                        unsafe_allow_html=True)
            edited = st.text_area(
                "",
                value=st.session_state.voice_transcript,
                height=120,
                key=f"transcript_edit_{interview_state.turn}",
                label_visibility="collapsed"
            )
            col_clr, col_sub = st.columns([1, 4])
            with col_clr:
                if st.button("🗑️ Clear", key=f"clr_{interview_state.turn}",
                             use_container_width=True):
                    st.session_state.voice_transcript = ""
                    # st.session_state.last_audio_hash = None
                    st.rerun()
            with col_sub:
                if st.button("Submit Answer →", type="primary",
                             key=f"sub_{interview_state.turn}",
                             use_container_width=True):
                    answer = edited.strip() or None
                    if answer:
                        st.session_state.voice_transcript = ""
                        st.session_state.last_audio_hash = None
        else:
            st.markdown(
                '<p style="text-align:center; color:#334155; font-size:0.85rem; '
                'margin-top:0.5rem;">Record above · after clearing, record again for new transcript</p>',
                unsafe_allow_html=True
            )

    # ── EVALUATION (same for both modes) ──────────────────────────────────
    if answer:
        st.session_state.current_hint = None

        with st.spinner("Evaluating..."):
            evaluation = evaluate_answer(
                interview_state.current_skill,
                st.session_state.current_question,
                answer
            )

        if st.session_state.get("hint_used"):
            evaluation = apply_hint_penalty(evaluation)
            st.session_state.hint_used = False

        quality = evaluation["quality"]

        cheat_result = detect_cheating(answer, interview_state.depth_level)
        if cheat_result["flagged"]:
            evaluation["cheat_flags"] = cheat_result
            if cheat_result["risk"] == "high":
                st.warning(f"⚠️ Authenticity: {', '.join(cheat_result['flags'])}")

        interview_state.record(st.session_state.current_question, answer, evaluation)

        questions_on_skill = sum(
            1 for t in interview_state.history
            if t.get("skill") == interview_state.current_skill
        )
        if questions_on_skill >= 2 and len(interview_state.skill_queue) > 1:
            interview_state.advance_skill()

        if should_end_interview(interview_state.history):
            st.session_state.interview_complete = True
            st.rerun()

        interview_state.depth_level = decide_next_level(interview_state.depth_level, quality)

        missing_concepts = evaluation.get("concepts", {}).get("missing", [])
        followup = None
        if missing_concepts and quality != "strong":
            from resume_engine.questions import generate_followup
            followup = generate_followup(
                interview_state.current_skill, missing_concepts, answer)

        st.session_state.current_question = followup or cached_generate_question(
            interview_state.current_skill,
            interview_state.depth_level,
            interview_state.asked_questions,
            profile,
            st.session_state.get("jd_text"),
            st.session_state.get("persona")
        )
        st.rerun()