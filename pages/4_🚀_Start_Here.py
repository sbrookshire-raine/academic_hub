"""
FVCC Onboarding — What College Should Be

Not a brochure. Not a maze of links. A straight answer to:
'What do I get, what does it cost, and what will I be able to do?'

Every program framed around what the student BUILDS, not credits they collect.
"""

import json
from pathlib import Path

import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data"


@st.cache_data
def _load(name):
    p = DATA / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


st.set_page_config(page_title="Start Here — FVCC", page_icon="🚀", layout="wide")

essentials = _load("student_essentials.json")
tuition = _load("tuition.json")
kb = _load("fvcc_knowledge_base.json")
programs = kb.get("programs", [])
costs = essentials.get("costs", {})
breakdown = costs.get("per_credit_breakdown", {})
fc = breakdown.get("flathead_county_resident", {})

# ═════════════════════════════════════════════════════════════════════════════
# HERO
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
    <div style="padding: 2rem 0 1rem 0; text-align: center;">
        <h1 style="font-size: 2.5rem; margin-bottom: 0.3rem;">You're here to build something real.</h1>
        <p style="font-size: 1.3rem; color: #666; max-width: 700px; margin: 0 auto;">
            Not to collect credits. Not to check boxes.<br>
            Every class you take should leave you with proof you can do the work.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# THE DEAL — HONEST COSTS
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("## The Deal")
st.markdown("Here's what it costs. No tabs to click. No PDFs to download. The actual number.")

deal_col1, deal_col2, deal_col3 = st.columns(3)

with deal_col1:
    st.markdown("### One Semester")
    st.markdown(f"# ${fc.get('semester_15cr', 3077.40):,.0f}")
    st.caption("15 credits · Flathead County resident")
    st.caption(f"${fc.get('total_per_credit', 205.16):.2f}/credit, tuition + fees included")

with deal_col2:
    st.markdown("### One Year")
    st.markdown(f"# ${fc.get('full_year_30cr', 6154.80):,.0f}")
    st.caption("30 credits · two semesters")

with deal_col3:
    st.markdown("### Full Degree")
    st.markdown(f"# ${fc.get('two_year_degree_60cr', 12309.60):,.0f}")
    st.caption("60 credits · Associate degree")

with st.expander("Not from Flathead County? Other rates"):
    mt = breakdown.get("montana_resident", {})
    oos = breakdown.get("out_of_state", {})
    wue = breakdown.get("wue", {})
    rate_cols = st.columns(3)
    with rate_cols[0]:
        st.metric("Montana Resident", f"${mt.get('total_per_credit', 261.42):.2f}/credit")
        st.caption(f"Semester: ${mt.get('semester_15cr', 3921.30):,.0f}")
    with rate_cols[1]:
        st.metric("Out-of-State", f"${oos.get('total_per_credit', 494.73):.2f}/credit")
        st.caption(f"Semester: ${oos.get('semester_15cr', 7420.95):,.0f}")
    with rate_cols[2]:
        st.metric("WUE (Western States)", f"${wue.get('total_per_credit', 345.12):.2f}/credit")
        st.caption(f"Semester: ${wue.get('semester_15cr', 5176.80):,.0f}")

st.markdown(
    """
    <div style="background: #1a1a2e; color: #e0e0e0; padding: 1.2rem 1.5rem; border-radius: 8px; margin: 1rem 0;">
        <strong>What the money gets you:</strong> Not just lectures. Access to labs, equipment, 
        mentors, career services, health clinic, tutoring, library, and a network. 
        The question isn't whether college is worth it — it's whether you use what you're paying for.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# THE MODEL — PROVE IT CULTURE
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("## The Model")
st.markdown("Every class should be a prototype. Here's what that means.")

model_col1, model_col2, model_col3 = st.columns(3)

with model_col1:
    st.markdown(
        """
        ### 🔨 Build Something
        Every class ends with something you made.
        A weld. A program. A patient care plan.
        A business proposal. A research paper with
        real data. Not a multiple choice test — a
        **thing that exists** because you did the work.
        """
    )

with model_col2:
    st.markdown(
        """
        ### 🤖 Use AI as a Tool
        AI doesn't replace learning — it accelerates it.
        Use it to research faster, prototype quicker,
        debug code, draft plans, analyze data. The skill
        isn't avoiding AI. It's knowing **how to direct it**
        and **verify the output**. That's the new literacy.
        """
    )

with model_col3:
    st.markdown(
        """
        ### 📂 Stack Your Work
        Everything you build adds up. Semester 1 feeds
        Semester 2. Your final project builds on your
        first one. When you graduate, you don't have a
        transcript — you have a **portfolio** of real work
        that proves you can do the job.
        """
    )

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# PICK YOUR PATH
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("## Pick Your Path")
st.markdown("What do you want to be able to do? Start there. Everything else follows.")

# Group programs by division with real framing
division_frames = {
    "Trades Institute": {
        "icon": "🔧",
        "pitch": "Build things. Fix things. Run things.",
        "output": "You leave with certifications, hands-on hours, and skills employers are hiring for right now.",
        "ai_angle": "Use AI for diagnostics, project estimation, code compliance lookup, and documentation.",
    },
    "Health Sciences": {
        "icon": "🏥",
        "pitch": "Take care of people.",
        "output": "Clinical hours, certifications, and the knowledge to keep someone alive.",
        "ai_angle": "Use AI for patient documentation, research, treatment protocols, and health data analysis.",
    },
    "Nursing": {
        "icon": "💉",
        "pitch": "Become an RN.",
        "output": "Pass the NCLEX. Work anywhere in the country. Competitive admission — earn your spot.",
        "ai_angle": "Use AI for care planning, pharmacology reference, evidence-based practice research.",
    },
    "Business and Technology": {
        "icon": "💼",
        "pitch": "Run a business. Manage money. Build systems.",
        "output": "Business plans, financial models, marketing campaigns, IT infrastructure — things companies need.",
        "ai_angle": "Use AI for market analysis, financial projections, automation, customer insights.",
    },
    "Math and Computer Science": {
        "icon": "💻",
        "pitch": "Write code. Solve problems. Build software.",
        "output": "Working applications, data analysis projects, algorithms that do real things.",
        "ai_angle": "AI is your pair programmer. Learn to architect, prompt, debug, and ship.",
    },
    "Science and Engineering": {
        "icon": "🔬",
        "pitch": "Understand how things work. Then make them better.",
        "output": "Lab reports with real data, research projects, engineering designs.",
        "ai_angle": "Use AI for data modeling, literature review, experimental design, visualization.",
    },
    "Humanities": {
        "icon": "📝",
        "pitch": "Think critically. Communicate clearly. Understand people.",
        "output": "Published writing, presentations, media projects, persuasive arguments.",
        "ai_angle": "Use AI for research, drafting, translation, content analysis — but YOUR voice matters.",
    },
    "Social Sciences": {
        "icon": "🌍",
        "pitch": "Understand communities. Solve human problems.",
        "output": "Case studies, community projects, policy analysis, fieldwork.",
        "ai_angle": "Use AI for data collection, survey analysis, trend research, program evaluation.",
    },
    "Culinary Arts": {
        "icon": "🍳",
        "pitch": "Feed people. Run a kitchen.",
        "output": "Menus, catering plans, food safety certs, and meals that people actually eat.",
        "ai_angle": "Use AI for menu costing, inventory management, nutrition analysis, scaling recipes.",
    },
}

# Build program lookup by division
programs_by_div = {}
for p in programs:
    div = p.get("division", "Other")
    programs_by_div.setdefault(div, []).append(p)

for div_name, frame in division_frames.items():
    div_programs = programs_by_div.get(div_name, [])
    if not div_programs:
        continue

    with st.expander(f"{frame['icon']} **{div_name}** — {frame['pitch']} ({len(div_programs)} programs)"):
        st.markdown(f"**What you walk away with:** {frame['output']}")
        st.markdown(f"**AI integration:** {frame['ai_angle']}")
        st.markdown("---")
        st.markdown("**Programs:**")
        for p in sorted(div_programs, key=lambda x: x.get("name", "")):
            name = p.get("name", "")
            dt = p.get("degree_type", "")
            credits = p.get("total_credits", "")
            cr_str = f" · {credits} credits" if credits else ""
            dt_labels = {
                "AAS": "Career degree",
                "AA": "Transfer degree",
                "AS": "Transfer degree",
                "CAS": "Certificate (~1 year)",
                "CTS": "Short certificate",
                "ASN": "Nursing degree",
            }
            dt_label = dt_labels.get(dt, dt)
            st.markdown(f"- **{name}** — {dt_label}{cr_str}")

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# HOW IT WORKS — 4 STEPS
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("## How It Works")
st.markdown("Four steps. Not forty-seven.")

step_cols = st.columns(4)

with step_cols[0]:
    st.markdown(
        """
        ### 1. Apply
        [Free. Online. 15 minutes.](https://slate.fvcc.edu/portal/fvcc_app)

        No fee. No essay. Rolling admission.
        """
    )

with step_cols[1]:
    st.markdown(
        """
        ### 2. Plan
        Meet an advisor. Pick your path.
        They register you the first time.

        📞 (406) 756-3880
        """
    )

with step_cols[2]:
    st.markdown(
        """
        ### 3. Fund It
        File your [FAFSA](https://studentaid.gov).
        FVCC code: **006777**.
        Most students qualify for aid.
        """
    )

with step_cols[3]:
    st.markdown(
        """
        ### 4. Show Up & Build
        Every class is a chance to create
        something real. Stack your work.
        Graduate with proof.
        """
    )

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# THE DIFFERENCE
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("## The Old Way vs. This Way")

diff_col1, diff_col2 = st.columns(2)

with diff_col1:
    st.markdown(
        """
        ### ❌ The Old Way
        - Navigate 100+ pages to find basic info
        - Credits are the goal
        - Tests measure memorization
        - AI is "cheating"
        - Graduate with a transcript
        - Figure it out yourself
        - Information hidden behind tabs and jargon
        - One-size-fits-all
        """
    )

with diff_col2:
    st.markdown(
        """
        ### ✅ This Way
        - Everything you need is right here
        - **Results** are the goal
        - Projects prove you can do the work
        - AI is a tool you learn to command
        - Graduate with a **portfolio**
        - Your path is mapped — focus on learning
        - Costs, deadlines, and steps are plain English
        - Your program, your pace, your proof
        """
    )

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
    <div style="text-align: center; padding: 2rem 0; color: #888;">
        <p style="font-size: 1.1rem;">The system changed. This is what's next.</p>
        <p style="font-size: 0.85rem;">
            Flathead Valley Community College · 777 Grandview Drive, Kalispell, MT 59901 · (406) 756-3822
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
