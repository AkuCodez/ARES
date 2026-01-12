# 🧠 ARES – AI Resume-Based Interview Simulator

ARES is an AI-powered interview platform that analyzes a candidate’s resume, generates a personalized technical interview, adaptively adjusts question difficulty based on performance, evaluates answers at a concept level, and produces a detailed interview report with strengths, weaknesses, and hiring recommendations.

🔗 Live Demo: https://ares-interview-prep.streamlit.app/

---

## 🚀 Features

### 📄 Resume Understanding
- Supports PDF and DOCX resume uploads
- Extracts key skills, education, and experience
- Handles edge cases like unreadable or scanned resumes with user-friendly errors

### 🎤 Adaptive Interview Engine
- Generates questions dynamically based on extracted skills
- Adjusts difficulty in real time depending on candidate responses
- Terminates interviews intelligently using performance-based logic:
  - Ends early for consistently strong candidates
  - Probes deeper for weak candidates
  - Enforces a hard cap to prevent infinite loops

### 🧠 Concept-Level Answer Evaluation
- Evaluates answers beyond correct/incorrect
- Identifies:
  - Concept coverage
  - Missing knowledge areas
  - Response quality (Strong / Medium / Weak)
- Produces structured feedback for every question

### 📊 Intelligent Interview Summary
- Aggregates performance across all questions
- Highlights:
  - Strong concepts
  - Repeated weaknesses
  - Overall hiring recommendation
- Provides actionable insights for improvement

### ⚡ Performance Optimized
- Uses Streamlit caching to avoid reprocessing resumes
- Minimal API calls for fast response times
- State-managed interview flow for smooth UX

---

## 🛠️ Tech Stack

- **Python**
- **Streamlit** (UI & deployment)
- **OpenAI API** (LLM-based analysis & evaluation)
- **PDF/DOCX Parsing**
- **Session State & Caching** for performance

---

## 🧩 System Architecture

