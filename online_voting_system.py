import os
import re
from html import escape as html_escape

import altair as alt
import bcrypt
import psycopg2
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="CampusVote · College Voting Portal",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 6
MAX_CANDIDATES = 10

# Code an admin must supply to self-register. Change this before deploying
# (e.g. via the ADMIN_SETUP_CODE environment variable) so students can't
# grant themselves admin access through the Registration page.
ADMIN_SETUP_CODE = os.environ.get("ADMIN_SETUP_CODE", "CollegeVote#2026")


# --------------------------------------------------------------------------
# Theme / CSS
# --------------------------------------------------------------------------

APP_CSS = """
<style>
/* ---------- base ---------- */
html, body, [class*="css"] {
    font-family: 'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', sans-serif;
}
.stApp {
    background:
        radial-gradient(1000px 500px at 92% -10%, rgba(139, 92, 246, .16), transparent 60%),
        radial-gradient(800px 420px at -10% 12%, rgba(99, 102, 241, .13), transparent 55%),
        radial-gradient(700px 380px at 50% 115%, rgba(217, 70, 239, .08), transparent 60%),
        #F6F7FF;
}
[data-testid="stHeader"] { background: transparent; }
.block-container, [data-testid="stMainBlockContainer"] {
    padding-top: 2.4rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}
h1, h2, h3, h4 { color: #1E1B4B; }
hr { border-color: #E2E8F0; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1E1B4B 0%, #312E81 55%, #3730A3 100%);
}
[data-testid="stSidebar"] * { color: #C7D2FE; }
.sb-brand {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 4px 18px;
    border-bottom: 1px solid rgba(199, 210, 254, .18);
    margin-bottom: 16px;
}
.sb-logo {
    width: 46px; height: 46px; border-radius: 14px; flex: 0 0 46px;
    display: flex; align-items: center; justify-content: center; font-size: 23px;
    background: linear-gradient(135deg, #6366F1, #A855F7);
    box-shadow: 0 6px 18px rgba(99, 102, 241, .5);
}
.sb-name { font-size: 1.18rem; font-weight: 800; color: #FFFFFF; letter-spacing: .3px; }
.sb-sub { font-size: .70rem; color: #A5B4FC; text-transform: uppercase; letter-spacing: 1.6px; }
.sb-foot {
    margin-top: 22px; padding-top: 14px;
    border-top: 1px solid rgba(199, 210, 254, .15);
    font-size: .72rem; color: #A5B4FC; text-align: center; letter-spacing: .4px;
    line-height: 1.7;
}

/* ---------- radio: cards in main area ---------- */
.stRadio div[role="radiogroup"] { gap: 10px; }
.stRadio div[role="radiogroup"] > label {
    background: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 14px;
    padding: 13px 18px;
    width: 100%;
    box-shadow: 0 2px 10px rgba(15, 23, 42, .04);
    transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
    cursor: pointer;
}
.stRadio div[role="radiogroup"] > label:hover {
    border-color: #A5B4FC;
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(99, 102, 241, .14);
}
.stRadio div[role="radiogroup"] > label:has(input:checked) {
    border-color: #6366F1;
    background: linear-gradient(135deg, rgba(99, 102, 241, .09), rgba(168, 85, 247, .09));
    box-shadow: 0 6px 20px rgba(99, 102, 241, .20);
}
.stRadio label p { font-weight: 600; color: #1E293B; }
.stRadio label > div:first-of-type { display: none; }

/* ---------- radio: nav pills in sidebar ---------- */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] { gap: 7px; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
    background: rgba(255, 255, 255, .05);
    border: 1px solid rgba(199, 210, 254, .12);
    border-radius: 12px;
    padding: 11px 15px;
    width: 100%;
    box-shadow: none;
    transition: background .18s ease, transform .18s ease;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
    background: rgba(255, 255, 255, .13);
    transform: translateX(3px);
    border-color: rgba(199, 210, 254, .25);
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(135deg, #6366F1, #8B5CF6);
    border-color: transparent;
    box-shadow: 0 6px 16px rgba(99, 102, 241, .55);
    transform: none;
}
[data-testid="stSidebar"] .stRadio label p { color: #E0E7FF !important; font-weight: 600; }

/* ---------- buttons ---------- */
.stButton > button, [data-testid="stFormSubmitButton"] > button {
    border-radius: 12px;
    font-weight: 700;
    padding: .55rem 1.4rem;
    border: 1.5px solid #C7D2FE;
    color: #4338CA;
    background: #FFFFFF;
    transition: all .18s ease;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
    border-color: #6366F1;
    color: #4F46E5;
    box-shadow: 0 6px 16px rgba(99, 102, 241, .22);
    transform: translateY(-1px);
}
.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 55%, #A855F7 100%);
    border: none;
    color: #FFFFFF;
    box-shadow: 0 8px 22px rgba(99, 102, 241, .45);
}
.stButton > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"]:hover {
    color: #FFFFFF;
    box-shadow: 0 12px 28px rgba(139, 92, 246, .55);
    transform: translateY(-2px);
}

/* ---------- forms, inputs, misc containers ---------- */
[data-testid="stForm"] {
    background: #FFFFFF;
    border: 1px solid #EEF0FF;
    border-radius: 18px;
    padding: 1.4rem 1.5rem;
    box-shadow: 0 10px 30px rgba(30, 27, 75, .08);
}
[data-testid="stForm"] h5 { color: #312E81; }
[data-baseweb="input"] {
    background: #F8FAFF !important;
    border: 1.5px solid #DDE3F0 !important;
    border-radius: 10px !important;
    transition: border-color .15s ease, box-shadow .15s ease;
}
[data-baseweb="input"]:focus-within {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, .16);
}
[data-baseweb="input"] input { background: transparent !important; }
[data-testid="stNumberInput"] button { background: #EEF2FF; border-radius: 8px; }
.stSelectbox [data-baseweb="select"] > div {
    background: #F8FAFF !important;
    border: 1.5px solid #DDE3F0 !important;
    border-radius: 10px !important;
}
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #EEF0FF;
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: 0 8px 24px rgba(30, 27, 75, .07);
}
[data-testid="stMetricLabel"] p { color: #64748B; font-weight: 600; }
[data-testid="stMetricValue"] { color: #312E81; font-weight: 800; }
[data-testid="stAlert"] {
    border-radius: 14px;
    box-shadow: 0 4px 14px rgba(15, 23, 42, .05);
}
[data-testid="stExpander"] {
    border: 1px solid #EEF0FF;
    border-radius: 16px;
    background: #FFFFFF;
    box-shadow: 0 6px 18px rgba(30, 27, 75, .06);
    overflow: hidden;
}
[data-testid="stExpander"] .stButton > button:hover {
    border-color: #F87171; color: #DC2626;
    box-shadow: 0 6px 16px rgba(248, 113, 113, .25);
}
[data-testid="stDataFrame"] {
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 6px 18px rgba(30, 27, 75, .06);
}

/* ---------- hero ---------- */
.hero {
    position: relative;
    background: linear-gradient(120deg, #4F46E5 0%, #7C3AED 50%, #C026D3 100%);
    border-radius: 22px;
    padding: 36px 40px 32px;
    margin-bottom: 26px;
    color: #FFFFFF;
    overflow: hidden;
    box-shadow: 0 18px 44px rgba(79, 70, 229, .35);
}
.hero::after {
    content: "";
    position: absolute; inset: 0;
    background:
        radial-gradient(240px 240px at 88% -25%, rgba(255, 255, 255, .28), transparent 70%),
        radial-gradient(190px 190px at 72% 125%, rgba(255, 255, 255, .16), transparent 70%),
        radial-gradient(120px 120px at 8% 110%, rgba(255, 255, 255, .12), transparent 70%);
    pointer-events: none;
}
.hero-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(255, 255, 255, .18);
    border: 1px solid rgba(255, 255, 255, .35);
    padding: 5px 15px;
    border-radius: 999px;
    font-size: .78rem; font-weight: 700; letter-spacing: 1px;
    margin-bottom: 15px;
}
.hero h1 {
    color: #FFFFFF;
    font-size: 2.55rem;
    font-weight: 850;
    margin: 0 0 8px;
    letter-spacing: -.5px;
    line-height: 1.15;
}
.hero p { color: #EDE9FE; font-size: 1.06rem; margin: 0; max-width: 620px; }

/* ---------- page header ---------- */
.page-head { display: flex; gap: 14px; align-items: center; margin: 2px 0 20px; }
.ph-icon {
    width: 54px; height: 54px; border-radius: 16px; flex: 0 0 54px;
    display: flex; align-items: center; justify-content: center; font-size: 27px;
    background: linear-gradient(135deg, #EEF2FF, #F3E8FF);
    border: 1px solid #E0E7FF;
    box-shadow: 0 6px 16px rgba(99, 102, 241, .15);
}
.page-head h2 { margin: 0; font-size: 1.55rem; font-weight: 800; color: #1E1B4B; }
.page-head p { margin: 2px 0 0; color: #64748B; font-size: .95rem; }

/* ---------- feature cards ---------- */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-top: 20px;
}
.feature-card {
    background: #FFFFFF;
    border: 1px solid #EEF0FF;
    border-radius: 18px;
    padding: 24px 22px;
    box-shadow: 0 8px 24px rgba(30, 27, 75, .06);
    transition: transform .18s ease, box-shadow .18s ease;
}
.feature-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 16px 36px rgba(99, 102, 241, .18);
}
.fc-icon {
    width: 48px; height: 48px; border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 23px; margin-bottom: 13px;
    background: linear-gradient(135deg, #6366F1, #A855F7);
    box-shadow: 0 8px 18px rgba(139, 92, 246, .38);
}
.feature-card h4 { margin: 0 0 6px; color: #1E1B4B; font-size: 1.05rem; font-weight: 800; }
.feature-card p { margin: 0; color: #64748B; font-size: .9rem; line-height: 1.55; }
@media (max-width: 780px) { .feature-grid { grid-template-columns: 1fr; } }

/* ---------- status banners / chips ---------- */
.status-banner {
    display: flex; align-items: center; gap: 10px;
    border-radius: 16px;
    padding: 15px 19px;
    margin: 18px 0 4px;
    font-weight: 600;
    font-size: .98rem;
}
.status-open {
    background: linear-gradient(120deg, #ECFDF5, #D1FAE5);
    border: 1px solid #6EE7B7;
    color: #065F46;
}
.status-closed {
    background: linear-gradient(120deg, #FFF7ED, #FFEDD5);
    border: 1px solid #FDBA74;
    color: #9A3412;
}
.election-chip {
    display: inline-flex; align-items: center; gap: 8px;
    background: #FFFFFF;
    border: 1px solid #E0E7FF;
    padding: 9px 18px;
    border-radius: 999px;
    font-weight: 800;
    color: #312E81;
    box-shadow: 0 4px 12px rgba(30, 27, 75, .07);
    margin: 14px 0 14px;
    font-size: 1.02rem;
}

/* ---------- winner card & vote share bars ---------- */
.winner-card {
    display: flex; align-items: center; gap: 16px;
    background: linear-gradient(120deg, #FEF3C7, #FDE68A);
    border: 1px solid #FCD34D;
    border-radius: 18px;
    padding: 16px 22px;
    margin: 4px 0 16px;
    box-shadow: 0 10px 26px rgba(245, 158, 11, .25);
}
.winner-card .wc-emoji { font-size: 36px; }
.wc-label {
    font-size: .72rem; letter-spacing: 1.4px; text-transform: uppercase;
    color: #92400E; font-weight: 800;
}
.wc-name { font-size: 1.35rem; font-weight: 850; color: #78350F; }
.wc-votes { margin-left: auto; text-align: right; color: #92400E; font-weight: 700; }

.share-list { display: flex; flex-direction: column; gap: 12px; margin: 6px 0 4px; }
.share-row {
    background: #FFFFFF;
    border: 1px solid #EEF0FF;
    border-radius: 14px;
    padding: 13px 17px;
    box-shadow: 0 4px 14px rgba(30, 27, 75, .05);
}
.share-top { display: flex; justify-content: space-between; margin-bottom: 9px; }
.share-name { font-weight: 700; color: #1E293B; }
.share-votes { color: #64748B; font-weight: 600; font-size: .88rem; }
.share-bar { height: 10px; border-radius: 999px; background: #EEF2FF; overflow: hidden; }
.share-bar .fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #818CF8, #8B5CF6);
    transition: width .6s ease;
}
.share-bar .fill.win { background: linear-gradient(90deg, #F59E0B, #F97316); }
</style>
"""

st.markdown(APP_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

@st.cache_resource
def get_connection():
    # Prefer a single DATABASE_URL (Supabase / Neon give you one). Fall back to
    # individual PG* variables, or local defaults for development.
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            host=os.environ.get("PGHOST", "localhost"),
            port=os.environ.get("PGPORT", "5432"),
            user=os.environ.get("PGUSER", "postgres"),
            password=os.environ.get("PGPASSWORD", "postgres"),
            dbname=os.environ.get("PGDATABASE", "voting_system"),
            sslmode=os.environ.get("PGSSLMODE", "prefer"),
        )
    conn.autocommit = False
    return conn


db = get_connection()
cursor = db.cursor()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, AttributeError):
        return False


def is_student_registered(student_id):
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    return cursor.fetchone()


def is_student_email_taken(email):
    cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
    return cursor.fetchone()


def is_admin_username_taken(username):
    cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
    return cursor.fetchone()


def is_admin_email_taken(email):
    cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
    return cursor.fetchone()


def has_voted(student_id, election_id):
    cursor.execute(
        "SELECT * FROM cast_vote WHERE student_id = %s AND election_id = %s",
        (student_id, election_id),
    )
    return cursor.fetchone() is not None


def record_vote(student_id, candidate_id, election_id):
    """Returns True on success, False if the student already voted (race-safe)."""
    try:
        cursor.execute(
            "INSERT INTO cast_vote (student_id, election_id) VALUES (%s, %s)",
            (student_id, election_id),
        )
        cursor.execute(
            "UPDATE candidates SET votes = votes + 1 WHERE candidate_id = %s",
            (candidate_id,),
        )
        db.commit()
        return True
    except psycopg2.IntegrityError:
        db.rollback()
        return False


def authenticate_student(student_id, password):
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    if student and verify_password(password, student[3]):
        return student
    return None


def authenticate_admin(username, password):
    cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
    admin = cursor.fetchone()
    if admin and verify_password(password, admin[3]):
        return admin
    return None


def register_student(sid, name, email, pw):
    cursor.execute(
        "INSERT INTO students (student_id, name, email, password) VALUES (%s, %s, %s, %s)",
        (sid, name, email, hash_password(pw)),
    )
    db.commit()


def register_admin(uname, email, pw):
    cursor.execute(
        "INSERT INTO admins (username, email, password) VALUES (%s, %s, %s)",
        (uname, email, hash_password(pw)),
    )
    db.commit()


def get_active_election():
    cursor.execute("SELECT * FROM elections WHERE election_status = 'Active'")
    return cursor.fetchone()


def get_candidates_by_election(election_id):
    cursor.execute("SELECT * FROM candidates WHERE election_id = %s", (election_id,))
    return cursor.fetchall()


def get_total_students():
    cursor.execute("SELECT COUNT(*) FROM students")
    return cursor.fetchone()[0]


def get_votes_cast(election_id):
    cursor.execute("SELECT COUNT(*) FROM cast_vote WHERE election_id = %s", (election_id,))
    return cursor.fetchone()[0]


# --------------------------------------------------------------------------
# UI helpers
# --------------------------------------------------------------------------

def page_header(icon, title, subtitle):
    st.markdown(
        f'<div class="page-head">'
        f'<div class="ph-icon">{icon}</div>'
        f'<div><h2>{html_escape(title)}</h2><p>{html_escape(subtitle)}</p></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def vote_share_bars(rows, highlight=None):
    """rows: list of (name, votes) tuples. Returns HTML for animated share bars."""
    total = sum(v for _, v in rows)
    out = ['<div class="share-list">']
    for name, votes in rows:
        pct = (votes / total * 100) if total else 0.0
        is_win = highlight is not None and name == highlight
        crown = " 🏆" if is_win else ""
        fill_cls = "fill win" if is_win else "fill"
        plural = "s" if votes != 1 else ""
        out.append(
            f'<div class="share-row">'
            f'<div class="share-top"><span class="share-name">{html_escape(str(name))}{crown}</span>'
            f'<span class="share-votes">{votes} vote{plural} · {pct:.1f}%</span></div>'
            f'<div class="share-bar"><div class="{fill_cls}" style="width:{pct:.1f}%"></div></div>'
            f'</div>'
        )
    out.append("</div>")
    return "".join(out)


def results_chart(election_df):
    return (
        alt.Chart(election_df)
        .mark_bar(
            size=46,
            cornerRadiusTopLeft=8,
            cornerRadiusTopRight=8,
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="#4F46E5", offset=0),
                    alt.GradientStop(color="#A78BFA", offset=1),
                ],
                x1=1, x2=1, y1=1, y2=0,
            ),
        )
        .encode(
            x=alt.X(
                "Candidate:N",
                sort="-y",
                axis=alt.Axis(labelAngle=0, title=None, labelColor="#475569", labelFontWeight="bold"),
            ),
            y=alt.Y(
                "Votes:Q",
                axis=alt.Axis(title=None, labelColor="#64748B", tickMinStep=1, format="d"),
            ),
            tooltip=["Candidate", "Votes"],
        )
        .properties(height=330)
        .configure_axis(gridColor="#E7E9FB", domain=False)
        .configure_view(strokeWidth=0)
    )


# --------------------------------------------------------------------------
# Session state & navigation
# --------------------------------------------------------------------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "vote_verified" not in st.session_state:
    st.session_state.vote_verified = False
if "verified_user_id" not in st.session_state:
    st.session_state.verified_user_id = None
if "menu" not in st.session_state:
    st.session_state.menu = "Home"

with st.sidebar:
    st.markdown(
        '<div class="sb-brand">'
        '<div class="sb-logo">🗳️</div>'
        '<div><div class="sb-name">CampusVote</div>'
        '<div class="sb-sub">College Elections</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.radio(
        "Navigation",
        ["Home", "Cast Vote", "Registration", "Admin", "Show Results"],
        key="menu",
        label_visibility="collapsed",
    )
    st.markdown(
        '<div class="sb-foot">🔒 Secure · Anonymous ballots<br>One student, one vote</div>',
        unsafe_allow_html=True,
    )

menu = st.session_state.menu

# --------------------------------------------------------------------------
# Home
# --------------------------------------------------------------------------

if menu == "Home":
    st.markdown(
        '<div class="hero">'
        '<div class="hero-badge">🎓 CAMPUSVOTE · SECURE STUDENT ELECTIONS</div>'
        '<h1>Your Voice. Your Campus. Your Vote. 🗳️</h1>'
        '<p>Cast your ballot in seconds — secure, anonymous, and strictly one vote per student. '
        'Every election, made fair and transparent.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    active_election = get_active_election()
    col1, col2, col3 = st.columns(3)
    col1.metric("👨‍🎓 Registered Students", get_total_students())
    if active_election:
        col2.metric("🗳️ Active Election", active_election[1])
        col3.metric("🏅 Candidates", len(get_candidates_by_election(active_election[0])))
        st.markdown(
            f'<div class="status-banner status-open">🟢 Voting is open for '
            f'<b>&nbsp;{html_escape(active_election[1])}&nbsp;</b> — head to '
            f'<b>&nbsp;Cast Vote&nbsp;</b> to participate!</div>',
            unsafe_allow_html=True,
        )
    else:
        col2.metric("🗳️ Active Election", "None")
        col3.metric("🏅 Candidates", 0)
        st.markdown(
            '<div class="status-banner status-closed">🟠 No election is running right now — '
            'check <b>&nbsp;Show Results&nbsp;</b> for past outcomes.</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="feature-grid">'
        '<div class="feature-card"><div class="fc-icon">📝</div><h4>1 · Register</h4>'
        '<p>Create your student account with your college ID and email. Takes under a minute.</p></div>'
        '<div class="feature-card"><div class="fc-icon">🗳️</div><h4>2 · Cast Your Vote</h4>'
        '<p>Verify with your ID and password, pick your candidate, submit. Your ballot stays anonymous.</p></div>'
        '<div class="feature-card"><div class="fc-icon">📊</div><h4>3 · See Results</h4>'
        '<p>Once the election ends, official results are published with vote counts and charts.</p></div>'
        '</div>',
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------
# Cast Vote
# --------------------------------------------------------------------------

elif menu == "Cast Vote":
    page_header("🗳️", "Cast Your Vote", "Verify your identity, choose your candidate — done in under a minute.")
    active_election = get_active_election()

    if not active_election:
        st.markdown(
            '<div class="status-banner status-closed">🟠 No active election at the moment. Check back later!</div>',
            unsafe_allow_html=True,
        )
    else:
        election_id = active_election[0]
        election_name = active_election[1]
        st.markdown(
            f'<div class="election-chip">🗳️ {html_escape(election_name)}</div>',
            unsafe_allow_html=True,
        )

        if not st.session_state.vote_verified:
            submitted = False
            left, mid, right = st.columns([1, 1.3, 1])
            with mid:
                with st.form("verify_form"):
                    st.markdown("##### 🔐 Voter Verification")
                    user_id = st.text_input("Student ID")
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button(
                        "Verify My Identity", type="primary", use_container_width=True
                    )

            if submitted:
                student = authenticate_student(user_id.strip(), password)
                if not student:
                    st.error("Invalid Student ID or Password.")
                elif has_voted(user_id.strip(), election_id):
                    st.warning("You have already voted in this election.")
                else:
                    st.session_state.vote_verified = True
                    st.session_state.verified_user_id = user_id.strip()
                    st.rerun()
        else:
            st.success(f"✅ Verified as **{st.session_state.verified_user_id}** — pick your candidate below.")
            if st.button("Not you? Switch account"):
                st.session_state.vote_verified = False
                st.session_state.verified_user_id = None
                st.rerun()

            candidates = get_candidates_by_election(election_id)
            if candidates:
                options = [c[0] for c in candidates]
                names = {c[0]: c[2] for c in candidates}
                selected_id = st.radio(
                    "Select a candidate to vote for:", options, format_func=lambda cid: names[cid]
                )

                col_a, col_b, col_c = st.columns([1, 1.2, 1])
                with col_b:
                    if st.button("🗳️ Submit My Vote", type="primary", use_container_width=True):
                        if has_voted(st.session_state.verified_user_id, election_id):
                            st.warning("You have already voted in this election.")
                        elif record_vote(st.session_state.verified_user_id, selected_id, election_id):
                            st.session_state.vote_verified = False
                            st.session_state.verified_user_id = None
                            st.success("✅ Vote submitted successfully! Thank you for participating.")
                            st.balloons()
                        else:
                            st.warning("You have already voted in this election.")
            else:
                st.error("No candidates found for this election.")

# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------

elif menu == "Registration":
    page_header("📝", "Registration", "Create your student or admin account.")
    left, mid, right = st.columns([1, 1.4, 1])

    with mid:
        reg_type = st.selectbox("Register as", ["Student", "Admin"])

        if reg_type == "Student":
            with st.form("student_reg_form"):
                st.markdown("##### 👨‍🎓 Student Registration")
                sid = st.text_input("Student ID (max 20 chars)")
                name = st.text_input("Name")
                email = st.text_input("Email")
                pw = st.text_input("Password", type="password")
                pw_confirm = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button(
                    "Register Student", type="primary", use_container_width=True
                )

            if submitted:
                sid = sid.strip()
                name = name.strip()
                email = email.strip()
                if not (sid and name and email and pw):
                    st.error("All fields are required.")
                elif not is_valid_email(email):
                    st.error("Please enter a valid email address.")
                elif len(pw) < MIN_PASSWORD_LEN:
                    st.error(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
                elif pw != pw_confirm:
                    st.error("Passwords do not match.")
                elif is_student_registered(sid[:20]):
                    st.error("Student ID already registered.")
                elif is_student_email_taken(email):
                    st.error("Email already registered.")
                else:
                    register_student(sid[:20], name, email, pw)
                    st.success("Student registered successfully! You can now go to Cast Vote.")

        elif reg_type == "Admin":
            with st.form("admin_reg_form"):
                st.markdown("##### 🧑‍💼 Admin Registration")
                uname = st.text_input("Username (max 20 chars)")
                email = st.text_input("Email")
                pw = st.text_input("Password", type="password")
                pw_confirm = st.text_input("Confirm Password", type="password")
                setup_code = st.text_input(
                    "Admin Setup Code", type="password",
                    help="Obtain this from your system administrator.",
                )
                submitted = st.form_submit_button(
                    "Register Admin", type="primary", use_container_width=True
                )

            if submitted:
                uname = uname.strip()
                email = email.strip()
                if not (uname and email and pw):
                    st.error("All fields are required.")
                elif setup_code != ADMIN_SETUP_CODE:
                    st.error("Invalid admin setup code.")
                elif not is_valid_email(email):
                    st.error("Please enter a valid email address.")
                elif len(pw) < MIN_PASSWORD_LEN:
                    st.error(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
                elif pw != pw_confirm:
                    st.error("Passwords do not match.")
                elif is_admin_username_taken(uname[:20]):
                    st.error("Username already exists.")
                elif is_admin_email_taken(email):
                    st.error("Email already registered.")
                else:
                    register_admin(uname[:20], email, pw)
                    st.success("Admin registered successfully!")

# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------

elif menu == "Admin":
    page_header("🧑‍💼", "Admin Panel", "Manage elections, monitor turnout, and view the student roster.")

    if not st.session_state.logged_in:
        submitted = False
        left, mid, right = st.columns([1, 1.2, 1])
        with mid:
            with st.form("admin_login_form"):
                st.markdown("##### 🔐 Admin Login")
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

        if submitted:
            if authenticate_admin(u.strip(), p):
                st.session_state.logged_in = True
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Login failed.")
    else:
        st.success("Welcome, Admin! 👋")
        admin_option = st.selectbox(
            "Options", ["Create Election", "End Election", "Live Monitor", "Registered Students"]
        )

        if admin_option == "Create Election":
            active_election = get_active_election()
            if active_election:
                st.warning(f"⚠️ An election is already active: **{active_election[1]}**. "
                           "Starting a new one will end it first.")

            name = st.text_input("Election Name")
            total = st.number_input(
                "Total Number of Candidates", min_value=2, max_value=MAX_CANDIDATES, step=1
            )

            if "candidate_names" not in st.session_state or len(st.session_state.candidate_names) != total:
                st.session_state.candidate_names = ["" for _ in range(total)]

            for i in range(total):
                st.session_state.candidate_names[i] = st.text_input(
                    f"Candidate {i + 1} Name", value=st.session_state.candidate_names[i]
                )

            confirm_replace = True
            if active_election:
                confirm_replace = st.checkbox("I confirm I want to end the current election and start a new one.")

            if st.button("🚀 Start Election", type="primary"):
                cleaned_names = [c.strip() for c in st.session_state.candidate_names if c.strip()]
                if not name.strip():
                    st.error("Election name is required.")
                elif len(cleaned_names) < 2:
                    st.error("At least 2 candidates with non-empty names are required.")
                elif len(set(cleaned_names)) != len(cleaned_names):
                    st.error("Candidate names must be unique.")
                elif active_election and not confirm_replace:
                    st.error("Please confirm you want to end the current election first.")
                else:
                    cursor.execute(
                        "UPDATE elections SET election_status = 'Ended' WHERE election_status = 'Active'"
                    )
                    db.commit()
                    cursor.execute(
                        "INSERT INTO elections (election_name, election_status) "
                        "VALUES (%s, %s) RETURNING election_id",
                        (name.strip(), "Active"),
                    )
                    election_id = cursor.fetchone()[0]
                    db.commit()

                    for cname in cleaned_names:
                        cursor.execute(
                            "INSERT INTO candidates (election_id, name, votes) VALUES (%s, %s, %s)",
                            (election_id, cname, 0),
                        )
                    db.commit()

                    del st.session_state["candidate_names"]
                    st.success(f"Election '{name}' created successfully!")

        elif admin_option == "End Election":
            active = get_active_election()
            if not active:
                st.warning("No active election.")
            else:
                election_id = active[0]
                election_name = active[1]

                cursor.execute(
                    "SELECT name, votes FROM candidates WHERE election_id = %s ORDER BY votes DESC",
                    (election_id,),
                )
                rows = cursor.fetchall()
                st.markdown(
                    f'<div class="election-chip">🗳️ Current standings — {html_escape(election_name)}</div>',
                    unsafe_allow_html=True,
                )
                leader = rows[0][0] if rows and rows[0][1] > 0 else None
                if rows:
                    st.markdown(vote_share_bars(rows, highlight=leader), unsafe_allow_html=True)

                if st.checkbox("I confirm I want to end this election. This cannot be undone."):
                    if st.button("End Election", type="primary"):
                        for cname, votes in rows:
                            cursor.execute(
                                "INSERT INTO election_results (election_id, election_name, candidate_name, votes) "
                                "VALUES (%s, %s, %s, %s)",
                                (election_id, election_name, cname, votes),
                            )

                        cursor.execute(
                            "UPDATE elections SET election_status = 'Ended' WHERE election_id = %s",
                            (election_id,),
                        )
                        db.commit()

                        cursor.execute("DELETE FROM candidates WHERE election_id = %s", (election_id,))
                        db.commit()

                        st.success("Election ended and results saved successfully!")

        elif admin_option == "Live Monitor":
            active = get_active_election()
            if not active:
                st.warning("No active election to monitor.")
            else:
                election_id = active[0]
                election_name = active[1]
                total_students = get_total_students()
                votes_cast = get_votes_cast(election_id)
                turnout = (votes_cast / total_students * 100) if total_students else 0

                col1, col2, col3 = st.columns(3)
                col1.metric("🗳️ Election", election_name)
                col2.metric("✅ Votes Cast", votes_cast)
                col3.metric("📈 Turnout", f"{turnout:.1f}%")

                cursor.execute(
                    "SELECT name, votes FROM candidates WHERE election_id = %s ORDER BY votes DESC",
                    (election_id,),
                )
                rows = cursor.fetchall()
                if rows:
                    leader = rows[0][0] if rows[0][1] > 0 else None
                    st.markdown(vote_share_bars(rows, highlight=leader), unsafe_allow_html=True)
                else:
                    st.info("No candidates found for this election.")
                st.caption("Live results are only visible to admins while an election is active, "
                           "to avoid influencing turnout.")

        elif admin_option == "Registered Students":
            search = st.text_input("🔍 Search by Student ID, Name, or Email")
            if search:
                like = f"%{search}%"
                cursor.execute(
                    "SELECT student_id, name, email, created_at FROM students "
                    "WHERE student_id ILIKE %s OR name ILIKE %s OR email ILIKE %s ORDER BY created_at DESC",
                    (like, like, like),
                )
            else:
                cursor.execute(
                    "SELECT student_id, name, email, created_at FROM students ORDER BY created_at DESC"
                )
            rows = cursor.fetchall()
            df = pd.DataFrame(rows, columns=["Student ID", "Name", "Email", "Registered At"])
            st.write(f"Total registered students: **{len(df)}**")
            st.dataframe(df, use_container_width=True)

        if st.button("Log Out"):
            st.session_state.logged_in = False
            st.success("Logged out successfully!")
            st.rerun()

# --------------------------------------------------------------------------
# Show Results
# --------------------------------------------------------------------------

elif menu == "Show Results":
    page_header("📊", "Election Results", "Official archived results of concluded elections.")

    cursor.execute(
        "SELECT election_name, candidate_name, votes FROM election_results ORDER BY result_time DESC"
    )
    results = cursor.fetchall()

    if not results:
        st.info("No election data available yet — results appear here once an election ends.")
    else:
        df = pd.DataFrame(results, columns=["Election", "Candidate", "Votes"])

        for election in df["Election"].unique():
            election_df = df[df["Election"] == election].copy()
            total_votes = int(election_df["Votes"].sum())
            winner_row = election_df.loc[election_df["Votes"].idxmax()]
            winner_name = str(winner_row["Candidate"])

            st.markdown(
                f'<div class="election-chip">🗳️ {html_escape(str(election))}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="winner-card"><div class="wc-emoji">🏆</div>'
                f'<div><div class="wc-label">Winner</div>'
                f'<div class="wc-name">{html_escape(winner_name)}</div></div>'
                f'<div class="wc-votes">{int(winner_row["Votes"])} of {total_votes} votes</div></div>',
                unsafe_allow_html=True,
            )

            chart_col, bars_col = st.columns([3, 2])
            with chart_col:
                st.altair_chart(results_chart(election_df), use_container_width=True, theme=None)
            with bars_col:
                bar_rows = list(
                    election_df.sort_values("Votes", ascending=False)[["Candidate", "Votes"]]
                    .itertuples(index=False, name=None)
                )
                st.markdown(
                    vote_share_bars(bar_rows, highlight=winner_name if total_votes else None),
                    unsafe_allow_html=True,
                )

    st.markdown("---")
    with st.expander("⚠️ Admin Control: Clear Votes & Results"):
        st.warning("This permanently deletes all vote records and past results. This cannot be undone.")
        admin_user = st.text_input("Admin Username", key="clear_admin_user")
        admin_pass = st.text_input("Admin Password", type="password", key="clear_admin_pass")
        confirm_clear = st.checkbox("I understand this action is irreversible.")

        if st.button("Confirm and Clear"):
            if not confirm_clear:
                st.error("Please confirm you understand this action is irreversible.")
            elif authenticate_admin(admin_user.strip(), admin_pass):
                try:
                    cursor.execute("DELETE FROM cast_vote")
                    cursor.execute("DELETE FROM election_results")
                    db.commit()
                    st.success("✅ All votes and results have been cleared.")
                except Exception as e:
                    db.rollback()
                    st.error(f"An error occurred: {e}")
            else:
                st.error("❌ Invalid admin credentials.")
