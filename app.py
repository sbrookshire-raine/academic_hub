"""
FVCC Academic Advising Hub
Landing page for the FVCC Course Planner multi-page application.
"""

import subprocess
import sys
from pathlib import Path

import streamlit as st


def _launched_via_streamlit() -> bool:
    """Return True when running inside Streamlit runtime."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


# If user runs `python app.py`, re-launch correctly through Streamlit.
if __name__ == "__main__" and not _launched_via_streamlit():
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(Path(__file__))], check=False)
    raise SystemExit(0)

# Auto-seed demo data on first run (e.g., fresh Streamlit Cloud deploy)
_db_path = Path(__file__).parent / "data" / "user_progress.db"
if not _db_path.exists():
    subprocess.run([sys.executable, str(Path(__file__).parent / "tools" / "seed_demo.py")], check=False)

st.set_page_config(
    page_title="FVCC Academic Advising",
    page_icon="🎓",
    layout="wide",
)

st.title("🎓 FVCC Academic Advising")
st.caption("Flathead Valley Community College")

st.markdown(
    """
    <div style="text-align: center; padding: 1.5rem 0; border-left: 4px solid #4A90D9; margin: 1rem 0; padding-left: 1.5rem;">
        <p style="font-size: 1.15rem; font-style: italic; color: #555; margin: 0;">
            "The easier a student can navigate the landscape and actually learn what they are tasked with,
            the better the institution has done in preparing the student for the future."
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

col_advisor, col_student = st.columns(2)

with col_advisor:
    st.markdown(
        """
        ### 🎓 I'm an Advisor

        Your workspace for supporting students.

        - See all your students and where each one stands
        - Map out what courses they've taken and what's next
        - Check prerequisites, schedules, and open seats
        - Answer student questions directly
        """
    )
    st.page_link("pages/1_🎓_Advisor_Dashboard.py", label="Open Advisor Dashboard", icon="🎓", use_container_width=True)

with col_student:
    st.markdown(
        """
        ### 📚 I'm a Student

        Your guide through your program.

        - See how far you've come and what's left
        - Know exactly which classes to take next
        - Check schedules, times, and open seats
        - Ask your advisor questions anytime
        """
    )
    st.page_link("pages/2_📚_Student_Portal.py", label="Open Student Portal", icon="📚", use_container_width=True)

st.markdown("---")

col_faq, col_start = st.columns(2)

with col_faq:
    st.markdown(
        """
        ### ❓ FAQ

        Plain answers to the questions students actually ask.
        Costs, financial aid, registration, jargon — no runaround.
        """
    )
    st.page_link("pages/3_❓_FAQ.py", label="Open FAQ", icon="❓", use_container_width=True)

with col_start:
    st.markdown(
        """
        ### 🚀 Start Here

        What college should look like. Honest costs, real outcomes,
        and a prove-it model where every class builds something.
        """
    )
    st.page_link("pages/4_🚀_Start_Here.py", label="Start Here", icon="🚀", use_container_width=True)

st.markdown("---")

st.page_link("pages/5_📋_Programs.py", label="📋 Browse All 67 Programs — costs, courses, availability", use_container_width=True)

st.markdown("---")

st.markdown(
    """
    <div style="text-align: center; color: #888; padding: 1.5rem 0;">
        <p>Less time figuring out logistics. More time for the conversations that matter.</p>
        <p style="font-size: 0.85rem;">Source: fvcc.edu · catalog.fvcc.edu · elements.fvcc.edu</p>
    </div>
    """,
    unsafe_allow_html=True,
)

