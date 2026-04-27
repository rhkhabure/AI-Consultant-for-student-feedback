"""
USIU-Africa AI Feedback Consultant
===================================
Single-file Streamlit app. Run locally with:
    streamlit run app.py

For Streamlit Cloud deployment:
    1. Push this file + feedback.db to a GitHub repo
    2. Add ANTHROPIC_API_KEY in the Streamlit Cloud secrets panel
    3. Deploy from the repo

Dependencies (requirements.txt):
    streamlit>=1.35.0
    anthropic>=0.25.0
    openpyxl>=3.1.0
"""

import os
import json
import hashlib
import sqlite3
import re
from pathlib import Path
from textwrap import dedent

import streamlit as st
import anthropic

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
# DB_PATH: looks for feedback.db next to app.py by default.
# Override with the DB_PATH environment variable if needed.
DB_PATH      = os.getenv("DB_PATH", str(Path(__file__).parent / "feedback.db"))
CLAUDE_MODEL = "claude-sonnet-4-5"
DEFAULT_PW   = "usiu2019"


# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG — must be the first Streamlit call
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="USIU Feedback Consultant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ══════════════════════════════════════════════════════════════════════════════
# STYLES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&display=swap');

:root {
  --ink:      #1a1812;
  --gold:     #b8953a;
  --gold-lt:  #d4af5a;
  --parch:    #f5f0e8;
  --warm:     #faf7f2;
  --border:   #e2d9c8;
  --muted:    #6b6356;
  --navy:     #1e2a3a;
  --navy-lt:  #2a3a4e;
  --success:  #2d6a4f;
  --danger:   #9b2335;
}

/* ── Base ── */
html, body, [class*="css"], .stApp {
  font-family: 'DM Sans', sans-serif !important;
  background: var(--warm) !important;
  color: var(--ink) !important;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.75rem 2.25rem 3rem !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] > div:first-child {
  background: var(--navy) !important;
  border-right: 1px solid rgba(184,149,58,0.2);
}
section[data-testid="stSidebar"] * { color: #ccc8be !important; }
section[data-testid="stSidebar"] .stMarkdown h3 { color: var(--gold-lt) !important; font-size: 0.78rem !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; }
section[data-testid="stSidebar"] .stMarkdown p  { font-size: 0.82rem !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(184,149,58,0.2) !important; margin: 0.6rem 0 !important; }

section[data-testid="stSidebar"] .stButton > button {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(184,149,58,0.25) !important;
  color: #b8b0a0 !important;
  font-size: 0.75rem !important;
  text-align: left !important;
  justify-content: flex-start !important;
  padding: 0.38rem 0.75rem !important;
  border-radius: 3px !important;
  width: 100% !important;
  transition: all 0.15s ease !important;
  margin-bottom: 2px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(184,149,58,0.14) !important;
  border-color: var(--gold) !important;
  color: var(--gold-lt) !important;
}

/* ── Main buttons ── */
.stButton > button {
  background: var(--navy) !important;
  color: var(--gold-lt) !important;
  border: 1px solid rgba(184,149,58,0.35) !important;
  border-radius: 4px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
  padding: 0.48rem 1.4rem !important;
  transition: all 0.15s ease !important;
}
.stButton > button:hover {
  background: var(--gold) !important;
  color: var(--navy) !important;
  border-color: var(--gold) !important;
}

/* ── Inputs ── */
div[data-testid="stTextInput"] input {
  background: var(--parch) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.88rem !important;
  color: var(--ink) !important;
  padding: 0.5rem 0.75rem !important;
}
div[data-testid="stTextInput"] input:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 3px rgba(184,149,58,0.12) !important;
}
div[data-testid="stTextInput"] label {
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  letter-spacing: 0.04em !important;
  color: var(--muted) !important;
}

/* ── Chat input ── */
div[data-testid="stChatInput"] textarea {
  background: white !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.88rem !important;
  color: var(--ink) !important;
}
div[data-testid="stChatInput"] textarea:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 3px rgba(184,149,58,0.12) !important;
}

/* ── Chat messages ── */
.stChatMessage { background: transparent !important; }

.msg-assistant {
  background: white;
  border: 1px solid var(--border);
  border-left: 3px solid var(--gold);
  border-radius: 0 8px 8px 8px;
  padding: 1.1rem 1.3rem;
  font-size: 0.875rem;
  line-height: 1.78;
  color: var(--ink);
  box-shadow: 0 1px 6px rgba(0,0,0,0.04);
  margin-bottom: 0.25rem;
}
.msg-assistant strong { color: var(--navy); }
.msg-assistant ul, .msg-assistant ol { padding-left: 1.2rem; margin: 0.4rem 0; }
.msg-assistant li { margin-bottom: 0.25rem; }

.msg-user {
  background: var(--navy);
  color: #ddd8ce !important;
  border-radius: 8px 8px 2px 8px;
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  line-height: 1.65;
  display: inline-block;
  max-width: 88%;
  float: right;
  clear: both;
  margin-bottom: 0.5rem;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: var(--gold) !important; }

/* ── Metric cards ── */
.metrics-strip {
  display: flex;
  gap: 0.65rem;
  margin-bottom: 1.2rem;
  flex-wrap: wrap;
}
.metric-card {
  background: white;
  border: 1px solid var(--border);
  border-top: 2px solid var(--gold);
  border-radius: 0 0 6px 6px;
  padding: 0.65rem 1rem 0.55rem;
  flex: 1;
  min-width: 110px;
}
.metric-card .val {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 1.7rem;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.1;
}
.metric-card .lbl {
  font-size: 0.62rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  margin-top: 3px;
}

/* ── Page heading ── */
.page-heading {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 1.9rem;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.15;
  margin-bottom: 0.15rem;
}
.page-sub {
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 1.1rem;
}

/* ── Login ── */
.login-card {
  background: white;
  border: 1px solid var(--border);
  border-top: 3px solid var(--gold);
  border-radius: 0 0 10px 10px;
  padding: 2.4rem 2rem 2rem;
  box-shadow: 0 8px 40px rgba(0,0,0,0.07);
}
.login-title {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 1.7rem;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 0.2rem;
}
.login-tagline {
  font-size: 0.65rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 1.8rem;
}
.login-hint {
  font-size: 0.68rem;
  color: #9a9080;
  margin-top: 1.25rem;
  line-height: 1.7;
}

/* ── Role badge ── */
.rbadge {
  display: inline-block;
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 2px;
  margin-left: 0.5rem;
  vertical-align: middle;
}
.rbadge-lecturer { background: #e8f4ec; color: #2d6a4f; }
.rbadge-dean     { background: #fdf3e0; color: #8a6020; }
.rbadge-vc       { background: #eeeaff; color: #4a3aa0; }

/* Alert boxes */
.alert-warn {
  background: #fdf3e0;
  border: 1px solid #e8c878;
  border-left: 3px solid var(--gold);
  border-radius: 4px;
  padding: 0.6rem 0.9rem;
  font-size: 0.8rem;
  color: #6b5020;
  margin-bottom: 0.75rem;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_db():
    if not Path(DB_PATH).exists():
        st.error(f"Database not found at: {DB_PATH}\nMake sure feedback.db is in the same folder as app.py.")
        st.stop()
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def q(sql: str, params: tuple = ()) -> list:
    return get_db().execute(sql, params).fetchall()


def q1(sql: str, params: tuple = ()):
    row = get_db().execute(sql, params).fetchone()
    return dict(row) if row else None


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def authenticate(username: str, password: str) -> dict | None:
    return q1(
        "SELECT u.*, f.full_name "
        "FROM users u LEFT JOIN faculty_metadata f ON u.faculty_id = f.faculty_id "
        "WHERE u.username = ? AND u.password_hash = ?",
        (username.strip().lower(), hash_pw(password)),
    )


# ══════════════════════════════════════════════════════════════════════════════
# DATA FETCHERS
# ══════════════════════════════════════════════════════════════════════════════

# Responses to skip when sampling comments for the AI prompt
_TRIVIAL = {
    "n/a", "na", "none", "nil", "ok", ".", "", "good", "nothing",
    "n.a", "not applicable", "no", "yes", "-", "none.", "nil.", "nill",
    "good.", "all", "everything", "nothing.", "okay", "okay.",
}


def _sample(responses: list, n: int = 50) -> list:
    """Return up to n non-trivial responses."""
    return [r for r in responses if r.lower().strip() not in _TRIVIAL and len(r) > 2][:n]


def get_lecturer_data(faculty_id: int) -> dict:
    sections = q(
        "SELECT s.*, f.full_name, f.title, f.is_adjunct, f.highest_degree "
        "FROM sections s JOIN faculty_metadata f ON s.faculty_id = f.faculty_id "
        "WHERE s.faculty_id = ? ORDER BY s.mean_score DESC NULLS LAST",
        (faculty_id,),
    )
    result = {"sections": []}
    for sec in sections:
        sd  = dict(sec)
        sid = sd["section_id"]
        sd["ce_questions"] = [
            dict(r) for r in q(
                "SELECT question_index, question_text, mean, dept_mean, all_college_mean "
                "FROM ce_question_scores WHERE section_id = ? ORDER BY question_index",
                (sid,),
            )
        ]
        sd["comments"] = {
            c["question_key"]: json.loads(c["responses"])
            for c in q("SELECT question_key, responses FROM comments WHERE section_id = ?", (sid,))
        }
        result["sections"].append(sd)
    return result


def get_dean_data(school: str) -> dict:
    sections = q(
        "SELECT s.*, f.full_name, f.is_adjunct, f.title "
        "FROM sections s JOIN faculty_metadata f ON s.faculty_id = f.faculty_id "
        "WHERE s.school = ? ORDER BY s.mean_score DESC NULLS LAST",
        (school,),
    )
    result = {"school": school, "sections": []}
    for sec in sections:
        sd  = dict(sec)
        sid = sd["section_id"]
        sd["ce_questions"] = [
            dict(r) for r in q(
                "SELECT question_index, question_text, mean "
                "FROM ce_question_scores WHERE section_id = ? ORDER BY question_index",
                (sid,),
            )
        ]
        sd["comments"] = {
            c["question_key"]: json.loads(c["responses"])
            for c in q("SELECT question_key, responses FROM comments WHERE section_id = ?", (sid,))
        }
        result["sections"].append(sd)
    return result


def get_vc_data() -> dict:
    return {
        "schools": [dict(r) for r in q(
            "SELECT school, "
            "COUNT(DISTINCT section_id) n_secs, COUNT(DISTINCT faculty_id) n_fac, "
            "ROUND(AVG(mean_score),3) avg_score, ROUND(AVG(respondent_pct),1) avg_resp, "
            "MIN(mean_score) min_score, MAX(mean_score) max_score "
            "FROM sections WHERE school IS NOT NULL AND mean_score IS NOT NULL "
            "GROUP BY school ORDER BY avg_score DESC"
        )],
        "top_lecs": [dict(r) for r in q(
            "SELECT f.full_name, s.school, ROUND(AVG(s.mean_score),3) avg "
            "FROM sections s JOIN faculty_metadata f ON s.faculty_id = f.faculty_id "
            "WHERE s.mean_score IS NOT NULL GROUP BY s.faculty_id "
            "ORDER BY avg DESC LIMIT 10"
        )],
        "bot_lecs": [dict(r) for r in q(
            "SELECT f.full_name, s.school, ROUND(AVG(s.mean_score),3) avg "
            "FROM sections s JOIN faculty_metadata f ON s.faculty_id = f.faculty_id "
            "WHERE s.mean_score IS NOT NULL GROUP BY s.faculty_id "
            "ORDER BY avg ASC LIMIT 10"
        )],
        "weakest_ceqs": [dict(r) for r in q(
            "SELECT question_text, ROUND(AVG(mean),3) avg_mean, COUNT(*) n "
            "FROM ce_question_scores "
            "GROUP BY question_index, question_text ORDER BY avg_mean ASC LIMIT 8"
        )],
    }


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

_PERSONA = dedent("""
    You are the AI Feedback Consultant for United States International University - Africa (USIU-Africa).
    You hold the 2019 undergraduate faculty evaluation data and deliver evidence-based insights
    to academic stakeholders.

    TONE: Speak like a trusted senior academic consultant — authoritative, warm, analytical.
    Use language like "The data reveals...", "Worth drawing attention to...",
    "Reading across the student comments...", "A pattern that merits action...".
    Be direct and specific. Avoid corporate jargon and generic advice.

    GROUNDING RULE: Every claim must come from the data provided to you.
    Never fabricate scores, names, rankings, or trends.
    When you identify a student theme, quote their actual words briefly.
    When you make a recommendation, tie it explicitly to what students said.

    FORMAT: Use **bold headers** to organise long responses.
    Use bullet points for lists of 4 or more items.
    Open every response with a crisp, informative first sentence — never a greeting.
""").strip()


def _build_lecturer_prompt(user: dict, data: dict) -> str:
    name  = user.get("full_name") or user["username"]
    parts = []

    for s in data["sections"]:
        ceqs    = s.get("ce_questions", [])
        scored  = sorted([q for q in ceqs if q.get("mean")], key=lambda x: x["mean"])
        weakest  = scored[:4]
        strongest = scored[-2:]

        ceq_txt = ""
        if weakest:
            ceq_txt += "\n  Weakest CE dimensions: " + "; ".join(
                f'Q{q["question_index"]+1} "{q["question_text"][:42]}…" = {q["mean"]:.2f}'
                for q in weakest
            )
        if strongest:
            ceq_txt += "\n  Strongest CE dimensions: " + "; ".join(
                f'Q{q["question_index"]+1} = {q["mean"]:.2f}' for q in strongest
            )

        comms = s.get("comments", {})
        c_txt = ""
        for key, label in [("enjoyed","Enjoyed"),("disliked","Disliked"),
                             ("improve","Suggestions"),("overall_eval","Overall eval")]:
            picks = _sample(comms.get(key, []), 7)
            if picks:
                c_txt += f'\n  {label}: ' + " | ".join(f'"{r}"' for r in picks)

        parts.append(
            f'\nSection: {s["course_code"]} {s["section_code"]} — {(s.get("course_name") or "")[:50]}'
            f'\nScore: {s.get("mean_score","N/A")} ({s.get("letter_grade","")})  '
            f'Respondents: {s.get("respondents","?")} / {s.get("total_students","?")} '
            f'({s.get("respondent_pct","?")}%)'
            f'\nCE average: {s.get("ce_avg_mean","N/A")} | Dept avg: {s.get("ce_avg_dept_mean","N/A")} | College avg: {s.get("ce_avg_college","N/A")}'
            f'{ceq_txt}'
            f'\nStudent comments:{c_txt}\n'
        )

    return (
        f"{_PERSONA}\n\n"
        f"ROLE: You are speaking with {name}, a USIU-Africa lecturer.\n"
        f"Data is scoped to THEIR sections only. Never speculate about other lecturers.\n"
        f"Primary goal: help them understand what students are experiencing and give\n"
        f"concrete, evidence-grounded pedagogical guidance.\n\n"
        f"THEIR SECTION DATA:\n{''.join(parts)}"
    )


def _build_dean_prompt(user: dict, data: dict) -> str:
    name   = user.get("full_name") or user["username"]
    school = data["school"]
    secs   = data["sections"]

    means = [s["mean_score"] for s in secs if s.get("mean_score")]
    avg   = round(sum(means) / len(means), 3) if means else "N/A"
    sorted_secs = sorted(secs, key=lambda x: x.get("mean_score") or 0, reverse=True)
    top3  = sorted_secs[:3]
    bot3  = sorted_secs[-3:]

    # School-wide weakest CE dimensions
    from collections import defaultdict
    ceq_agg = defaultdict(list)
    for s in secs:
        for ceq in s.get("ce_questions", []):
            if ceq.get("mean"):
                ceq_agg[(ceq["question_index"], ceq["question_text"])].append(ceq["mean"])
    weakest_ceqs = sorted(
        ((idx, txt, round(sum(v)/len(v), 3)) for (idx, txt), v in ceq_agg.items()),
        key=lambda x: x[2]
    )[:5]

    # Aggregated comment samples
    enjoyed_s, disliked_s, improve_s = [], [], []
    for s in secs:
        c = s.get("comments", {})
        enjoyed_s  += _sample(c.get("enjoyed",  []), 3)
        disliked_s += _sample(c.get("disliked", []), 3)
        improve_s  += _sample(c.get("improve",  []), 3)

    top_txt = "\n".join(
        f'  {s["full_name"][:32]:32} | {s["course_code"]} {s["section_code"]} '
        f'| score={s.get("mean_score")} | {s.get("letter_grade","")}'
        for s in top3
    )
    bot_txt = "\n".join(
        f'  {s["full_name"][:32]:32} | {s["course_code"]} {s["section_code"]} '
        f'| score={s.get("mean_score")} | {s.get("letter_grade","")}'
        for s in bot3
    )
    ceq_txt = "\n".join(
        f'  {score:.3f}  {txt[:70]}' for _, txt, score in weakest_ceqs
    )
    roster = "\n".join(
        f'  {s["full_name"][:32]:32} | {s["course_code"]} {s["section_code"]} '
        f'| score={s.get("mean_score","?")} | {s.get("letter_grade","?")} '
        f'| adj={"Y" if s.get("is_adjunct") else "N"}'
        for s in secs
    )

    return (
        f"{_PERSONA}\n\n"
        f"ROLE: You are speaking with {name}, Dean of {school}.\n"
        f"You can see ALL sections in your school only.\n"
        f"Primary goal: surface patterns, rank lecturers with evidence, identify school-level themes,\n"
        f"and recommend interventions grounded in what students actually said.\n\n"
        f"SCHOOL OVERVIEW: {school}\n"
        f"Total sections: {len(secs)}  |  School average mean: {avg}\n\n"
        f"TOP 3 SECTIONS:\n{top_txt}\n\n"
        f"BOTTOM 3 SECTIONS:\n{bot_txt}\n\n"
        f"WEAKEST CE DIMENSIONS ACROSS SCHOOL:\n{ceq_txt}\n\n"
        f"STUDENT VOICE — ENJOYED: {' | '.join(f'{chr(34)}{r}{chr(34)}' for r in enjoyed_s[:10])}\n\n"
        f"STUDENT VOICE — DISLIKED: {' | '.join(f'{chr(34)}{r}{chr(34)}' for r in disliked_s[:10])}\n\n"
        f"STUDENT VOICE — SUGGESTIONS: {' | '.join(f'{chr(34)}{r}{chr(34)}' for r in improve_s[:10])}\n\n"
        f"FULL SECTION ROSTER:\n{roster}"
    )


def _build_vc_prompt(data: dict) -> str:
    schools_txt = "\n".join(
        f'  {s["school"][:40]:40} | avg={s["avg_score"]} | resp={s["avg_resp"]}% '
        f'| secs={s["n_secs"]} | fac={s["n_fac"]}'
        for s in data["schools"]
    )
    top_txt = "\n".join(
        f'  {l["full_name"][:35]:35} | {l["school"][:28]} | avg={l["avg"]}'
        for l in data["top_lecs"]
    )
    bot_txt = "\n".join(
        f'  {l["full_name"][:35]:35} | {l["school"][:28]} | avg={l["avg"]}'
        for l in data["bot_lecs"]
    )
    ceq_txt = "\n".join(
        f'  {q["avg_mean"]:.3f}  {q["question_text"][:70]}'
        for q in data["weakest_ceqs"]
    )
    return (
        f"{_PERSONA}\n\n"
        f"ROLE: You are speaking with the Vice Chancellor / institutional leadership of USIU-Africa.\n"
        f"You have institution-wide view of the 2019 undergraduate evaluations.\n"
        f"Focus on cross-school comparisons, systemic patterns, and strategic recommendations.\n\n"
        f"SCHOOL PERFORMANCE OVERVIEW:\n{schools_txt}\n\n"
        f"TOP 10 LECTURERS INSTITUTION-WIDE:\n{top_txt}\n\n"
        f"LOWEST 10 LECTURERS INSTITUTION-WIDE:\n{bot_txt}\n\n"
        f"WEAKEST TEACHING DIMENSIONS INSTITUTION-WIDE:\n{ceq_txt}"
    )


def build_system_prompt(user: dict, data: dict) -> str:
    role = user["role"]
    if role == "lecturer":
        return _build_lecturer_prompt(user, data)
    elif role == "dean":
        return _build_dean_prompt(user, data)
    else:
        return _build_vc_prompt(data)


# ══════════════════════════════════════════════════════════════════════════════
# CLAUDE INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════

def _opening_prompt(role: str) -> str:
    return {
        "lecturer": (
            "Good morning. I've reviewed the student evaluation data for my sections. "
            "Please give me a full briefing: quantitative performance per section, "
            "the key themes students are raising in their comments, my weakest and strongest "
            "CE dimensions by question, and three specific evidence-grounded recommendations "
            "I can act on immediately."
        ),
        "dean": (
            "Good morning. I need a full school briefing. Cover overall school performance, "
            "identify my top and lowest performing lecturers with evidence from student comments, "
            "highlight school-wide patterns in the qualitative feedback — especially themes that "
            "recur across multiple lecturers — and give me three concrete interventions I should "
            "prioritise this semester."
        ),
        "vc": (
            "Good morning. Please provide an executive briefing on our 2019 undergraduate "
            "faculty evaluation results. I want a cross-school comparison with clear analysis of "
            "where we are strong and where we have risk, identification of systemic patterns, "
            "and three strategic recommendations for institutional action."
        ),
    }[role]


def stream_claude(system: str, messages: list) -> str:
    """Stream a Claude response and render it live. Returns the full response text."""
    client = anthropic.Anthropic()
    full   = ""
    ph     = st.empty()

    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=1600,
        system=system,
        messages=messages,
    ) as stream:
        for chunk in stream.text_stream:
            full += chunk
            ph.markdown(
                f'<div class="msg-assistant">{full}▌</div>',
                unsafe_allow_html=True,
            )

    ph.markdown(f'<div class="msg-assistant">{full}</div>', unsafe_allow_html=True)
    return full


def get_opening_report(system: str, role: str) -> str:
    """Generate the initial briefing (non-streaming, returns full text)."""
    client = anthropic.Anthropic()
    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=1800,
        system=system,
        messages=[{"role": "user", "content": _opening_prompt(role)}],
    ) as stream:
        return stream.get_final_text()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

_SUGGESTIONS = {
    "lecturer": [
        "Which of my sections needs the most urgent attention?",
        "What are students consistently praising across my sections?",
        "What are my 3 weakest CE dimensions — with evidence from comments?",
        "How do I compare to the department and college averages?",
        "Give me a concrete improvement plan for my lowest-rated section.",
    ],
    "dean": [
        "Who is my strongest lecturer and what are they doing right?",
        "Which lecturer needs the most immediate support and why?",
        "What themes appear consistently across multiple sections?",
        "How do adjunct staff compare to full-time faculty in my school?",
        "Which sections have the biggest gap between score and comments?",
    ],
    "vc": [
        "Which school is performing best and what is driving that?",
        "What systemic weaknesses appear across all schools?",
        "Which lecturers should I recognise publicly?",
        "What are the top 3 policy changes the data recommends?",
        "How does our student response rate affect data reliability?",
    ],
}


def render_sidebar(user: dict, data: dict):
    role = user["role"]
    name = user.get("full_name") or user["username"]

    badge_styles = {
        "lecturer": "background:#e8f4ec;color:#2d6a4f;",
        "dean":     "background:#fdf3e0;color:#8a6020;",
        "vc":       "background:#eeeaff;color:#4a3aa0;",
    }

    with st.sidebar:
        # Logo
        st.markdown(
            '<div style="padding:0.5rem 0.5rem 1rem;">'
            '<div style="font-family:Cormorant Garamond,Georgia,serif;font-size:1.2rem;'
            'color:#d4af5a;font-weight:600;line-height:1.2;">USIU Feedback<br>Consultant</div>'
            '<div style="font-size:0.6rem;letter-spacing:0.13em;text-transform:uppercase;'
            'color:#6b6050;margin-top:3px;">Academic Intelligence · 2019</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Identity block
        st.markdown(
            f'<div style="font-size:0.88rem;font-weight:500;color:#ddd8ce;">{name}</div>'
            f'<span style="{badge_styles[role]}font-size:0.58rem;font-weight:700;'
            f'letter-spacing:0.12em;text-transform:uppercase;padding:2px 7px;border-radius:2px;">'
            f'{role.upper()}</span>',
            unsafe_allow_html=True,
        )
        if user.get("school"):
            st.markdown(
                f'<div style="font-size:0.72rem;color:#8a8070;margin-top:5px;">'
                f'{user["school"]}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("---")

        # Quick stats
        st.markdown("### Data at a glance")
        if role == "lecturer":
            secs  = data["sections"]
            means = [s["mean_score"] for s in secs if s.get("mean_score")]
            st.markdown(f"Sections: **{len(secs)}**")
            if means:
                st.markdown(f"Avg score: **{round(sum(means)/len(means), 2)}**")
        elif role == "dean":
            secs  = data["sections"]
            means = [s["mean_score"] for s in secs if s.get("mean_score")]
            n_fac = len(set(s["faculty_id"] for s in secs if s.get("faculty_id")))
            st.markdown(f"Sections: **{len(secs)}**  ·  Faculty: **{n_fac}**")
            if means:
                st.markdown(f"School avg: **{round(sum(means)/len(means), 2)}**")
        else:
            schools = data["schools"]
            total   = sum(s["n_secs"] for s in schools)
            st.markdown(f"Schools: **{len(schools)}**  ·  Sections: **{total}**")

        st.markdown("---")

        # Suggested questions
        st.markdown("### Ask the consultant")
        for s in _SUGGESTIONS[role]:
            if st.button(s, key=f"sug_{hash(s)}", use_container_width=True):
                st.session_state["pending"] = s
                st.rerun()

        st.markdown("---")

        # Sign out
        if st.button("Sign out", use_container_width=True, key="signout"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# METRIC CARDS
# ══════════════════════════════════════════════════════════════════════════════

def render_metrics(user: dict, data: dict):
    role = user["role"]

    if role == "lecturer":
        secs  = data["sections"]
        means = [s["mean_score"] for s in secs if s.get("mean_score")]
        cards = [
            (len(secs), "Sections"),
            (f"{round(sum(means)/len(means), 2)}" if means else "—", "Avg Score"),
            (f"{max(means):.2f}" if means else "—", "Best Section"),
            ([s.get("letter_grade","") for s in secs][0] if secs else "—", "Top Grade"),
        ]
    elif role == "dean":
        secs  = data["sections"]
        means = [s["mean_score"] for s in secs if s.get("mean_score")]
        n_fac = len(set(s["faculty_id"] for s in secs if s.get("faculty_id")))
        n_adj = sum(1 for s in secs if s.get("is_adjunct"))
        cards = [
            (len(secs), "Sections"),
            (f"{round(sum(means)/len(means), 2)}" if means else "—", "School Avg"),
            (n_fac, "Lecturers"),
            (n_adj, "Adjunct Staff"),
        ]
    else:
        schools = data["schools"]
        total   = sum(s["n_secs"] for s in schools)
        best    = schools[0]["avg_score"] if schools else "—"
        n_fac   = sum(s["n_fac"] for s in schools)
        cards   = [
            (len(schools), "Schools"),
            (total, "Total Sections"),
            (best, "Highest School Avg"),
            (n_fac, "Total Faculty"),
        ]

    html = '<div class="metrics-strip">'
    for val, lbl in cards:
        html += f'<div class="metric-card"><div class="val">{val}</div><div class="lbl">{lbl}</div></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════

def render_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.1, 1])

    with col:
        st.markdown(
            '<div class="login-card">'
            '<div class="login-title">USIU Feedback<br>Consultant</div>'
            '<div class="login-tagline">Academic Performance Intelligence · 2019 Undergraduate</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="username")
        password = st.text_input("Password", type="password", placeholder="password")

        btn_col, hint_col = st.columns([2, 1.2])
        with btn_col:
            login_btn = st.button("Sign In →", use_container_width=True)
        with hint_col:
            st.markdown(
                '<div style="font-size:0.68rem;color:#9a9080;padding-top:0.55rem;text-align:center;">'
                'Default pw: usiu2019</div>',
                unsafe_allow_html=True,
            )

        if login_btn:
            if not username.strip() or not password:
                st.error("Please enter both username and password.")
                return
            user = authenticate(username, password)
            if user:
                st.session_state["user"]     = user
                st.session_state["messages"] = []
                st.session_state["report"]   = None
                st.rerun()
            else:
                st.error("Username or password is incorrect.")

        st.markdown(
            '<div class="login-hint">'
            '<strong>Test accounts</strong><br>'
            'Deans: tndungu · aogada · sbironga · enyabere<br>'
            'VC: vc_admin<br>'
            'Lecturers: pafundi · eterefe · condiek'
            '</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

def render_app():
    user = st.session_state["user"]
    role = user["role"]

    # ── Load data + build system prompt once per session ─────────────────────
    if "system_prompt" not in st.session_state:
        with st.spinner("Loading your data…"):
            if role == "lecturer":
                data = get_lecturer_data(user["faculty_id"])
            elif role == "dean":
                data = get_dean_data(user["school"])
            else:
                data = get_vc_data()

            st.session_state["data"]          = data
            st.session_state["system_prompt"] = build_system_prompt(user, data)

    system_prompt = st.session_state["system_prompt"]
    data          = st.session_state["data"]

    # ── Sidebar ───────────────────────────────────────────────────────────────
    render_sidebar(user, data)

    # ── Page header ───────────────────────────────────────────────────────────
    role_titles = {
        "lecturer": "Lecturer Dashboard",
        "dean":     f"Dean · {user.get('school', 'School')}",
        "vc":       "Vice Chancellor — Institutional Overview",
    }
    st.markdown(
        f'<div class="page-heading">{role_titles[role]}</div>'
        f'<div class="page-sub">2019 Undergraduate Faculty Evaluation · USIU-Africa</div>',
        unsafe_allow_html=True,
    )

    # ── Metric cards ──────────────────────────────────────────────────────────
    render_metrics(user, data)

    st.markdown("---")

    # ── Generate opening report on first load ─────────────────────────────────
    if st.session_state.get("report") is None:
        opening_prompt = _opening_prompt(role)
        with st.spinner("Preparing your briefing…"):
            report = get_opening_report(system_prompt, role)

        st.session_state["report"] = report
        st.session_state["messages"] = [
            {"role": "user",      "content": opening_prompt},
            {"role": "assistant", "content": report},
        ]

    # ── Render message history ────────────────────────────────────────────────
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(
                    f'<div class="msg-user">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
        else:
            with st.chat_message("assistant"):
                st.markdown(
                    f'<div class="msg-assistant">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

    # ── Chat input ─────────────────────────────────────────────────────────────
    # Check for pending input from sidebar suggestion buttons
    pending    = st.session_state.pop("pending", None)
    user_input = st.chat_input("Ask anything about the feedback data…")
    if pending and not user_input:
        user_input = pending

    if user_input:
        # Show user message
        with st.chat_message("user"):
            st.markdown(
                f'<div class="msg-user">{user_input}</div>',
                unsafe_allow_html=True,
            )
        st.session_state["messages"].append({"role": "user", "content": user_input})

        # Stream the response
        with st.chat_message("assistant"):
            response = stream_claude(system_prompt, st.session_state["messages"])

        st.session_state["messages"].append({"role": "assistant", "content": response})


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if "user" not in st.session_state:
    render_login()
else:
    render_app()
