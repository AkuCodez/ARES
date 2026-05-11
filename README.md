<div align="center">

# ⚡ ARES
### AI Resume-Based Interview System

*An intelligent technical interview simulator that reads your resume and interviews you on it.*

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-orange?style=flat)](https://groq.com)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

[**Live Demo →**](https://your-app.streamlit.app) &nbsp;·&nbsp; [Report Bug](issues) &nbsp;·&nbsp; [GitHub](https://github.com/AkuCodez/ARES)

</div>

---

## What is ARES?

ARES uploads your resume, extracts what you claim to know, and interviews you on it — adaptively. Wrong answers get harder follow-ups. Right answers unlock deeper probing. It ends with a hire/no-hire verdict, skill gap analysis, and a downloadable PDF report.

**Built to demonstrate:** LLM orchestration, adaptive state machines, multi-modal input, real-time evaluation pipelines — not a chatbot wrapper.

---

## Features

| Category | Capability |
|---|---|
| **Resume Parsing** | PDF + DOCX extraction, LLM skill identification, confidence scoring, overclaim detection |
| **Adaptive Interview** | Depth-aware questioning (1→3), multi-skill rotation, follow-up probing on gaps |
| **Evaluation** | Per-answer scoring (correctness, depth, clarity), concept coverage tracking |
| **Anti-Cheat** | Filler ratio analysis, AI essay structure detection, advanced-term-at-basic-depth flags |
| **Voice Input** | Audio recording → Groq Whisper transcription, editable before submit |
| **Personas** | Friendly / FAANG / Startup / Academic — changes question style and tone |
| **JD Matching** | Paste a job description to bias questions toward that role |
| **Reporting** | Radar chart, confidence timeline, hire verdict, ReportLab PDF download |
| **Study Plan** | LLM-generated personalized gap analysis with resources and time estimates |

---

## Architecture

```
ARES/
├── app.py                    # Streamlit UI — all phases, custom CSS
├── resume_engine/
│   ├── llm_client.py         # Groq client (OpenAI SDK, custom base_url)
│   ├── models.py             # ResumeProfile, SkillInfo, InterviewState
│   ├── extract_text.py       # PDF + DOCX → raw text
│   ├── skill_extractor.py    # LLM → structured skill profile
│   ├── skills.py             # Skill taxonomy, concept graph, bootstrap
│   ├── questions.py          # Question generation, follow-ups, hints, personas
│   ├── evaluator.py          # Answer scoring, concept analysis, hint penalty
│   ├── policy.py             # Depth decisions, confidence computation
│   ├── anticheat.py          # Authenticity heuristics
│   ├── skill_gaps.py         # Study plan generation
│   ├── report.py             # ReportLab PDF builder
│   └── run_pipeline.py       # Resume → InterviewState orchestrator
└── dynamic_concepts.json     # Bootstrapped skill concept cache
```

**Data flow:**
```
Resume → extract_text → skill_extractor → estimate_skill_depth
       → InterviewState → [question loop] → evaluate_answer
       → decide_next_level → detect_cheating → record()
       → should_end → compute_confidence → generate_skill_gaps → PDF
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **UI** | Streamlit · Plotly · custom CSS (Syne + JetBrains Mono) |
| **LLM** | Groq API · `llama-3.3-70b-versatile` · `whisper-large-v3` |
| **PDF** | PyMuPDF (extract) · ReportLab (generate) |
| **Voice** | `audio-recorder-streamlit` · Groq Whisper transcription |
| **Document** | `python-docx` for DOCX resume support |
| **Charts** | Plotly radar + timeline charts |
| **Secrets** | `python-dotenv` local · Streamlit Cloud secrets dashboard |

---

## Setup

```bash
# 1. Clone
git clone https://github.com/AkuCodez/ARES
cd ARES

# 2. Install
pip install -r requirements.txt

# 3. Configure
echo "GROQ_API_KEY=your_key_here" > .env

# 4. Run
streamlit run app.py
```

> **Groq free tier:** 500k tokens/hour. If the app stalls, wait ~1hr or rotate your key.

---

## Interview Flow

```
Upload Resume
     │
     ▼
Skill Extraction + Depth Estimation
     │
     ▼
Select Persona → [Friendly | FAANG | Startup | Academic]
     │
     ▼
Question Loop ─────────────────────────────────────┐
     │                                             │
     ├─ Evaluate answer (correctness/depth/clarity)│
     ├─ Detect cheating heuristics                 │
     ├─ Probe missing concepts (follow-up)         │
     ├─ Adjust depth (strong→+1, weak→-1)          │
     └─ Rotate skill after 2 questions ────────────┘
     │
     ▼
End Condition Met (≥6 questions | 2× strong | repeated gaps)
     │
     ▼
Verdict + Radar Chart + Timeline + Study Plan + PDF
```

---

## Key Design Decisions

**Why Groq over OpenAI?**
Free tier, ~10× faster inference on LLaMA 70B — essential for real-time interview feel.

**Why `json_object` response format everywhere?**
Eliminates regex parsing. All LLM outputs are structured dicts — no hallucinated formats.

**Why no `@st.cache_data` on `cached_run()`?**
`InterviewState` contains sets and custom objects — not serializable by Streamlit's cache. Cleared manually post-upload instead.

**Why `_parse_depth()` as a classmethod?**
LLM occasionally returns `"foundation"` or `"applied"` instead of integers. Centralizes text→int conversion so depth arithmetic never crashes.

---

## Roadmap

- [ ] Shareable scorecard via Supabase (UUID public URL)
- [ ] Full UI redesign — enterprise dashboard layout
- [ ] Real-time transcription (streaming Whisper)
- [ ] Multi-language resume support
- [ ] Candidate comparison across sessions

---

## Author

**Akshaj** · VIT Vellore · [GitHub @AkuCodez](https://github.com/AkuCodez)

> *ARES was built as a demonstration of production-grade LLM system design — adaptive state, structured outputs, multi-modal input, and real evaluation logic — not a thin wrapper around a chat API.*

---

<div align="center">
<sub>Powered by Groq · Built with Streamlit · Not your average side project</sub>
</div>
