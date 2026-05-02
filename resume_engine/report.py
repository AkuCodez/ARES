# resume_engine/report.py
# Generates a downloadable PDF interview report using reportlab

from io import BytesIO
from collections import Counter
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)


# ── Palette ────────────────────────────────────────────────────────────────
_PURPLE     = colors.HexColor("#7C3AED")
_PURPLE_LT  = colors.HexColor("#EDE9FE")
_GREEN      = colors.HexColor("#16A34A")
_RED        = colors.HexColor("#DC2626")
_YELLOW     = colors.HexColor("#D97706")
_GREY       = colors.HexColor("#6B7280")
_DARK       = colors.HexColor("#111827")


def generate_report(profile, interview_state) -> bytes:
    """
    Build a styled PDF interview report and return raw bytes.
    Call BytesIO result directly with st.download_button.

    Args:
        profile:          ResumeProfile object
        interview_state:  InterviewState object

    Returns:
        PDF as bytes
    """
    buf    = BytesIO()
    doc    = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=48, rightMargin=48,
        topMargin=48,  bottomMargin=48
    )
    styles = getSampleStyleSheet()
    story  = []

    # ── Custom styles ──────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "ARESTitle",
        fontSize=24, textColor=_PURPLE,
        spaceAfter=4, fontName="Helvetica-Bold"
    )
    h2_style = ParagraphStyle(
        "ARESH2",
        fontSize=14, textColor=_DARK,
        spaceBefore=14, spaceAfter=4,
        fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "ARESBody",
        fontSize=10, textColor=_DARK,
        leading=15, fontName="Helvetica"
    )
    small_style = ParagraphStyle(
        "ARESSmall",
        fontSize=9, textColor=_GREY,
        fontName="Helvetica"
    )
    verdict_map = {
        "strong": ("Strong", _GREEN),
        "okay":   ("Okay",   _YELLOW),
        "weak":   ("Weak",   _RED),
    }

    # ── Header ─────────────────────────────────────────────────────────────
    story.append(Paragraph("ARES Interview Report", title_style))
    story.append(Paragraph(
        "AI Resume-Based Interview System", small_style
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=_PURPLE, spaceAfter=12
    ))

    # ── Overall verdict ────────────────────────────────────────────────────
    history       = interview_state.history
    verdicts      = [t["quality"]["quality"].lower() for t in history]
    verdict_count = Counter(verdicts)
    total         = len(history)
    strong_n      = verdict_count.get("strong", 0)

    if strong_n >= 2:
        hire_label, hire_color = "Strong Yes",        _GREEN
    elif strong_n == 1:
        hire_label, hire_color = "Borderline",        _YELLOW
    else:
        hire_label, hire_color = "Needs Improvement", _RED

    overall_score = sum(
        {"strong": 1.0, "okay": 0.5, "weak": 0.0}.get(v, 0)
        for v in verdicts
    ) / max(total, 1)

    summary_data = [
        ["Total Questions", "Overall Score", "Hire Recommendation"],
        [
            str(total),
            f"{overall_score:.0%}",
            hire_label
        ]
    ]
    summary_table = Table(summary_data, colWidths=[150, 150, 200])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), _PURPLE),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_PURPLE_LT, colors.white]),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.white),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 16))

    # ── Verdict breakdown ──────────────────────────────────────────────────
    story.append(Paragraph("Performance Breakdown", h2_style))
    breakdown_data = [["Verdict", "Count", "Percentage"]]
    for v in ["strong", "okay", "weak"]:
        n   = verdict_count.get(v, 0)
        pct = f"{n / max(total, 1):.0%}"
        breakdown_data.append([v.title(), str(n), pct])

    breakdown_table = Table(breakdown_data, colWidths=[150, 100, 100])
    breakdown_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), _DARK),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("GRID",        (0, 0), (-1, -1), 0.5, _GREY),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(breakdown_table)
    story.append(Spacer(1, 16))

    # ── Skill scores ───────────────────────────────────────────────────────
    story.append(Paragraph("Skill Scores", h2_style))
    skill_scores: dict = {}
    for turn in history:
        skill  = turn.get("skill", "Unknown")
        scores = turn.get("quality", {}).get("scores", {})
        if skill not in skill_scores:
            skill_scores[skill] = []
        skill_scores[skill].append(scores)

    skill_data = [["Skill", "Correctness", "Depth", "Clarity"]]
    for skill, score_list in skill_scores.items():
        def avg(dim):
            vals = [s.get(dim, 0) for s in score_list]
            return f"{sum(vals) / len(vals):.1f}/10" if vals else "N/A"
        skill_data.append([skill, avg("correctness"), avg("depth"), avg("clarity")])

    skill_table = Table(skill_data, colWidths=[180, 100, 100, 100])
    skill_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), _PURPLE),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("ALIGN",       (0, 1), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_PURPLE_LT, colors.white]),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.white),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(skill_table)
    story.append(Spacer(1, 16))

    # ── Concepts ───────────────────────────────────────────────────────────
    all_mentioned: list = []
    all_missing:   list = []
    for turn in history:
        c = turn.get("quality", {}).get("concepts", {})
        if c:
            all_mentioned.extend(c.get("mentioned", []))
            all_missing.extend(c.get("missing", []))

    if all_mentioned or all_missing:
        story.append(Paragraph("Concept Coverage", h2_style))
        concept_data = [["Strong Concepts", "Needs Work"]]
        top_mentioned = [c for c, _ in Counter(all_mentioned).most_common(6)]
        top_missing   = [c for c, _ in Counter(all_missing).most_common(6)]
        rows = max(len(top_mentioned), len(top_missing))
        for i in range(rows):
            concept_data.append([
                top_mentioned[i] if i < len(top_mentioned) else "",
                top_missing[i]   if i < len(top_missing)   else ""
            ])

        concept_table = Table(concept_data, colWidths=[240, 240])
        concept_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (0, 0), _GREEN),
            ("BACKGROUND",  (1, 0), (1, 0), _RED),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 10),
            ("ALIGN",       (0, 0), (-1, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ("GRID",        (0, 0), (-1, -1), 0.5, _GREY),
            ("TOPPADDING",  (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(concept_table)
        story.append(Spacer(1, 16))

    # ── Q&A transcript ─────────────────────────────────────────────────────
    story.append(Paragraph("Interview Transcript", h2_style))
    story.append(HRFlowable(width="100%", thickness=1, color=_GREY, spaceAfter=8))

    for i, turn in enumerate(history, 1):
        verdict_raw             = turn["quality"]["quality"].lower()
        verdict_text, v_color   = verdict_map.get(verdict_raw, ("Unknown", _GREY))

        story.append(Paragraph(
            f"<b>Q{i} [{turn.get('skill', '')} | Depth {turn.get('depth', '')}]</b>",
            ParagraphStyle("QLabel", fontSize=9, textColor=_PURPLE, fontName="Helvetica-Bold")
        ))
        story.append(Paragraph(turn["question"], body_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"<b>Answer:</b> {turn['answer']}", body_style
        ))
        story.append(Spacer(1, 4))

        verdict_style = ParagraphStyle(
            "Verdict", fontSize=9, textColor=v_color,
            fontName="Helvetica-Bold"
        )
        story.append(Paragraph(f"Verdict: {verdict_text}", verdict_style))
        story.append(Paragraph(
            turn["quality"].get("feedback", ""), small_style
        ))
        story.append(HRFlowable(
            width="100%", thickness=0.5,
            color=_GREY, spaceBefore=8, spaceAfter=8
        ))

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Generated by ARES — AI Resume-Based Interview System",
        ParagraphStyle("Footer", fontSize=8, textColor=_GREY,
                       fontName="Helvetica", alignment=1)
    ))

    doc.build(story)
    return buf.getvalue()