"""
FVCC Student FAQ
Plain answers to the questions students actually ask.
"""

import json
from pathlib import Path

import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data"


@st.cache_data
def load_essentials():
    p = DATA / "student_essentials.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


@st.cache_data
def load_tuition():
    p = DATA / "tuition.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


st.set_page_config(page_title="FVCC FAQ", page_icon="❓", layout="wide")

st.title("❓ Student FAQ")
st.caption("Plain answers. No runaround.")

essentials = load_essentials()
tuition = load_tuition()
costs = essentials.get("costs", {})
breakdown = costs.get("per_credit_breakdown", {})
fin_aid = essentials.get("financial_aid", {})
calendar = essentials.get("calendar", {})
reg = essentials.get("registration", {})
support = essentials.get("support_services", {}).get("services", {})
degree_types = essentials.get("degree_types", {}).get("types", {})
translations = essentials.get("website_translation", {}).get("translations", {})

# ── Search ───────────────────────────────────────────────────────────────────

search = st.text_input("🔍 Search for a question", placeholder="tuition, FAFSA, advising, placement...")

# ── Build FAQ entries ────────────────────────────────────────────────────────

fc = breakdown.get("flathead_county_resident", {})
mt = breakdown.get("montana_resident", {})
oos = breakdown.get("out_of_state", {})
wue = breakdown.get("wue", {})

faqs = [
    # ── MONEY ──
    {
        "category": "💰 Money",
        "q": "How much does FVCC cost?",
        "a": f"""**Per credit (tuition + fees):**
- Flathead County resident: **${fc.get('total_per_credit', 205.16):.2f}**
- Other Montana resident: **${mt.get('total_per_credit', 261.42):.2f}**
- Out-of-state: **${oos.get('total_per_credit', 494.73):.2f}**
- WUE (western states): **${wue.get('total_per_credit', 345.12):.2f}**

A typical semester (15 credits) for a Flathead County resident is about **${fc.get('semester_15cr', 3077.40):,.2f}**.
A full 2-year degree (60 credits) runs about **${fc.get('two_year_degree_60cr', 12309.60):,.2f}**.""",
    },
    {
        "category": "💰 Money",
        "q": "Are there hidden costs?",
        "a": """Yes. On top of tuition:
- **Lab fees** — some classes charge $20-200+ extra (not on the tuition schedule)
- **Textbooks** — budget $300-600/semester
- **Program supplies** — nursing, welding, culinary, trades all have material costs
- **Parking** — if you drive to campus""",
    },
    {
        "category": "💰 Money",
        "q": "When is tuition due?",
        "a": """**At registration.** If you can't pay in full, a deferred payment plan auto-applies:
- Fall/Spring: 25% in 4 monthly installments
- Summer: 33% in 3 installments

Miss a payment? **$25 late fee** each time. Bounced check? **$30 fee.**

If you don't pay at all: registration blocked, transcripts held, and they can send you to Montana Dept of Revenue collections (they'll take your tax refund).""",
    },
    {
        "category": "💰 Money",
        "q": "How do I get financial aid?",
        "a": """1. **File the FAFSA** at [studentaid.gov](https://studentaid.gov) — FVCC's code is **006777**
2. File **early** — priority deadline is **December 1** for spring, **March 1** for fall
3. You need an FSA ID (create one at studentaid.gov — parents too if you're under 24)
4. You'll need prior-prior year tax info (2024 taxes for 2026-2027)
5. Contact FVCC Financial Aid for any extra paperwork: **(406) 756-3849**

**You must re-file every year.**""",
    },
    {
        "category": "💰 Money",
        "q": "What financial aid can I get?",
        "a": """- **Pell Grant**: Up to $6,195/year. Free money, don't pay it back. Based on need.
- **FSEOG Grant**: Extra $200-500/year for the neediest students.
- **Federal Loans**: $5,500-$6,500/year. Low interest, but you DO pay these back. 6-month grace period after you leave school.
- **Work-Study**: Part-time campus job, up to 19 hrs/week. You get a paycheck (it doesn't pay tuition directly).
- **Scholarships**: [Apply here](https://www.fvcc.edu/admissions-financial-aid/financial-aid-scholarships/scholarships). Many go unclaimed because nobody applies.

Financial Aid Office: Student Center 117 · (406) 756-3849 · finaidinfo@fvcc.edu · Walk-in M-F 8am-5pm""",
    },

    # ── GETTING STARTED ──
    {
        "category": "🚀 Getting Started",
        "q": "How do I apply?",
        "a": """1. Go to [slate.fvcc.edu/portal/fvcc_app](https://slate.fvcc.edu/portal/fvcc_app) — **it's free**
2. Or apply through [Apply Montana](https://applymontana.mus.edu)
3. Takes 15-30 minutes
4. FVCC accepts applications on a rolling basis, but apply at least a week before the semester starts""",
    },
    {
        "category": "🚀 Getting Started",
        "q": "What do I do after I apply?",
        "a": """1. **Submit documents** — high school transcript or GED, college transcripts if transferring, ACT/SAT scores if you have them
2. **Take placement tests** (maybe — see below)
3. **Meet with an advisor** — call (406) 756-3880 to schedule
4. **Register for classes** — your advisor does this with you the first time
5. **Pay or set up financial aid**""",
    },
    {
        "category": "🚀 Getting Started",
        "q": "Do I need placement tests?",
        "a": """**Maybe not.** You can skip them if:
- You have ACT scores from the last 2 years: math 18+ and English 18+/writing 7+
- You're transferring with college math/English credits

**If you need them:**
- **Math**: Register through Student Portal → Student Resources → Advising Portal → Placement. It's online through EdReady.
- **Reading/Writing**: Accuplacer test, on campus or remote.

**Pro tip:** After your initial math placement, you can study and retest UP TO TWO LEVELS higher through the EdReady Study Path. Deadline is 3rd week of the semester.""",
    },

    # ── REGISTRATION ──
    {
        "category": "📋 Registration",
        "q": "How do I register for classes?",
        "a": """**New students:** Your advisor registers you at your first meeting. Call (406) 756-3880 to schedule.

**Returning students:** Register through the [Student Portal](https://elements.fvcc.edu/student/login.asp) once your registration window opens. Meet with your advisor first.

**Zoom walk-ins:** M-F 10am-2pm at [fvcc.zoom.us/j/93114034480](https://fvcc.zoom.us/j/93114034480)""",
    },
    {
        "category": "📋 Registration",
        "q": "When can I register?",
        "a": """Registration opens in order — sophomores first, then returning students, then new students.

**For Fall 2026:**
- April 1: Sophomores
- April 2: Returning students
- April 15: New degree-seeking students
- May 6: Running Start & non-degree

**Register early.** Popular classes (mornings, online) fill up fast.""",
    },
    {
        "category": "📋 Registration",
        "q": "What if I need to drop a class?",
        "a": """**Drop early.** The deadlines matter:
- **100% refund**: First few days (varies by session)
- **50% refund**: About a week in (0% after that)
- **Drop without a W**: Same early window
- **Withdraw with a W**: Weeks later, but you still owe the full amount

A "W" shows on your transcript but doesn't hurt your GPA. You still pay for it though.""",
    },

    # ── PROGRAMS ──
    {
        "category": "🎓 Programs & Degrees",
        "q": "What's the difference between AA, AS, AAS, CAS, and CTS?",
        "a": """- **AA (Associate of Arts)**: 2-year transfer degree for liberal arts. Transfers to 4-year schools.
- **AS (Associate of Science)**: 2-year transfer degree for science/math/engineering. Transfers to 4-year schools.
- **AAS (Associate of Applied Science)**: 2-year career degree. You graduate and go to work. Usually doesn't transfer cleanly.
- **CAS (Certificate of Applied Science)**: ~1 year focused career certificate.
- **CTS (Certificate of Technical Studies)**: Short certificate for a specific skill (CDL, CNA, EMT, etc.)

**Quick rule:** Transfer to a 4-year school → AA or AS. Job now → AAS or CAS. Quick credential → CTS.""",
    },
    {
        "category": "🎓 Programs & Degrees",
        "q": "Can I transfer my credits to a 4-year school?",
        "a": """**AA and AS degrees are designed to transfer** to Montana university system schools.

If you complete the Montana Core (general education requirements), those credits are **guaranteed to transfer** — that's called "Core Complete."

AAS degrees usually don't transfer cleanly, but some have specific articulation agreements. Ask your advisor about your specific situation.""",
    },

    # ── CAMPUS LIFE ──
    {
        "category": "🏫 Campus & Support",
        "q": "What free help is available?",
        "a": """All of these are **free** for students:
- **Tutoring** — most subjects, on campus
- **TRIO Support** — mentoring for first-gen/low-income students
- **Mental health counseling** — on campus
- **Food pantry** — no questions asked
- **Health clinic** — basic medical care (covered by your fees at 7+ credits)
- **Disability support** — accommodations for documented disabilities (register early!)
- **Career services** — resume help, job searching, internships
- **Library** — study rooms, equipment loans, research help
- **IT help** — login problems, email, Canvas issues
- **Veterans center** — VA benefits processing and vet community""",
    },
    {
        "category": "🏫 Campus & Support",
        "q": "Who do I call?",
        "a": """- **General / Admissions**: (406) 756-3822
- **Registration / Advising**: (406) 756-3880 · registrationinfo@fvcc.edu
- **Financial Aid**: (406) 756-3849 · finaidinfo@fvcc.edu
- **Business Office (payments)**: (406) 756-3831
- **Lincoln County Campus**: (406) 293-2721
- **Advising Zoom walk-in**: [fvcc.zoom.us/j/93114034480](https://fvcc.zoom.us/j/93114034480) M-F 10am-2pm""",
    },

    # ── JARGON ──
    {
        "category": "🔤 What Does That Mean?",
        "q": "What is 'Satisfactory Academic Progress' (SAP)?",
        "a": "Keep a **2.0 GPA** and pass at least **67% of your classes**, or you lose financial aid. You also have to finish your degree within 150% of the program length (60-credit degree = 90 attempted credits max).",
    },
    {
        "category": "🔤 What Does That Mean?",
        "q": "What's a 'credit hour'?",
        "a": "One credit = roughly one hour of class per week for a semester. A 3-credit class meets about 3 hours/week. **Full-time** is 12+ credits. **Half-time** is 6-11 credits (matters for financial aid and loan deferment).",
    },
    {
        "category": "🔤 What Does That Mean?",
        "q": "What are Session A, B, and C?",
        "a": "The semester is split into chunks. **Session A** = first 8 weeks. **Session B** = second 8 weeks. **Session C** = the full 16-week semester. Some classes are only 8 weeks long — you take them faster but they're more intense.",
    },
    {
        "category": "🔤 What Does That Mean?",
        "q": "What's WUE?",
        "a": "**Western Undergraduate Exchange.** If you live in a western state (WA, OR, ID, WY, ND, SD, NM, AZ, NV, UT, CO, HI, AK, etc.), you pay about 150% of in-state tuition instead of the full out-of-state rate. You have to apply for it.",
    },
    {
        "category": "🔤 What Does That Mean?",
        "q": "What's 'Eagle Online'?",
        "a": "That's **Canvas** — where your online classes and course materials live. You log in at [fvcc.instructure.com](https://fvcc.instructure.com).",
    },
    {
        "category": "🔤 What Does That Mean?",
        "q": "What does 'hold' or 'flag' on my account mean?",
        "a": "Something is blocking your account — usually an **unpaid balance** or a **missing document**. You can't register until it's cleared. Call the office that placed the hold.",
    },
]

# ── Filter by search ─────────────────────────────────────────────────────────

if search:
    search_lower = search.lower()
    faqs = [f for f in faqs if search_lower in f["q"].lower() or search_lower in f["a"].lower() or search_lower in f["category"].lower()]
    if not faqs:
        st.warning(f"No results for '{search}'. Try a different word.")
        st.stop()

# ── Render ───────────────────────────────────────────────────────────────────

current_category = ""
for faq in faqs:
    if faq["category"] != current_category:
        current_category = faq["category"]
        st.markdown(f"### {current_category}")

    with st.expander(faq["q"]):
        st.markdown(faq["a"])
