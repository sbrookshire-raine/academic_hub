"""
FVCC Student Portal
A calm, supportive dashboard where students can see their path,
track progress, and get the support they need.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from course_ui import render_course_schedule
from eligibility import analyze_schedule_registration_notes
from planner_helpers import (
    build_completed_course_codes,
    build_unlock_map,
    count_completed_credits,
    count_program_credits,
    count_remaining_slots,
    get_sections_for_course,
    get_selected_course_for_slot,
    iter_course_slots,
    merge_completed_course_codes,
    recommended_course_items,
    slot_display_label,
    slot_is_completed,
    sync_completed_slot_terms,
    term_status_badge,
)
from topic_lookup import get_all_essential_topics, get_essential_links, get_topic_pages
from progress_store import build_progress_store

DATA = Path(__file__).resolve().parent.parent / "data"
DB = Path(__file__).resolve().parent.parent / "db"
USER_PROGRESS_DB_PATH = DATA / "user_progress.db"
USER_PROGRESS_PATH = DATA / "user_progress.json"
PROGRESS_STORE = build_progress_store("sqlite", USER_PROGRESS_DB_PATH, USER_PROGRESS_PATH, DB / "migrations")


@st.cache_data
def _load_json(path_str: str, mtime_ns: int):
    del mtime_ns
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def _load(filename: str):
    p = DATA / filename
    if not p.exists():
        return {}
    return _load_json(str(p), p.stat().st_mtime_ns)


# ── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="FVCC Student Portal", page_icon="📚", layout="wide")

# ── Load Data ────────────────────────────────────────────────────────────────

pc = _load("program_courses.json")
sched = _load("schedules.json")
course_requirements_data = _load("course_requirements.json")
user_progress = PROGRESS_STORE.load()
course_requirements = course_requirements_data.get("courses", {})
unlock_map = build_unlock_map(course_requirements)
course_index = sched.get("course_index", {})
terms = sorted(sched.get("metadata", {}).get("terms", []))
programs_with_courses = [p for p in pc.get("programs", []) if any(s["courses"] for s in p["semesters"])]
essentials = _load("student_essentials.json")

# ── Student Selection ────────────────────────────────────────────────────────

student_records = user_progress.get("students", {})

if not student_records:
    st.title("📚 FVCC Student Portal")
    st.info("Your profile hasn't been set up yet. Ask your advisor to add you, then come back here.")
    st.stop()

# Sidebar — student picker (simple, friendly)
st.sidebar.markdown("### 👋 Who are you?")
student_ids = sorted(student_records.keys(), key=lambda sid: student_records[sid]["name"].lower())
student_name_map = {student_records[sid]["name"]: sid for sid in student_ids}
student_names = list(student_name_map.keys())

active_id = user_progress.get("active_student_id", "")
default_idx = 0
if active_id in student_records:
    try:
        default_idx = student_names.index(student_records[active_id]["name"])
    except ValueError:
        pass

selected_name = st.sidebar.selectbox("Select your name", student_names, index=default_idx)
selected_student_id = student_name_map[selected_name]
student = student_records[selected_student_id]

# Term selector
st.sidebar.markdown("### 📅 Term")
default_term_idx = terms.index("Fall 2026") if "Fall 2026" in terms else 0
selected_term = st.sidebar.selectbox("Viewing schedule for", terms, index=default_term_idx)

# ── Resolve Program ──────────────────────────────────────────────────────────

program_name = student.get("program_name", "")
program = next((p for p in programs_with_courses if p["name"] == program_name), None)

if not program:
    st.title(f"Welcome, {student['name']}! 📚")
    st.warning("Your advisor hasn't picked your program yet. Check back soon or ask them about it.")
    st.stop()

# ── Compute Progress ─────────────────────────────────────────────────────────

program_slots = iter_course_slots(program["semesters"])
for slot_idx, slot in enumerate(program_slots):
    slot["slot_id"] = f"{program['name']}::{slot_idx}::{slot['semester_label']}::{slot['group_idx']}"

completion_options = [slot_display_label(slot) for slot in program_slots if any(not c.get("is_elective") for c in slot["group"])]
completion_lookup = {
    slot_display_label(slot): slot["slot_id"]
    for slot in program_slots
    if any(not c.get("is_elective") for c in slot["group"])
}

completed_labels = [label for label in student.get("completed_slots", []) if label in completion_options]
completed_slot_ids = {completion_lookup[label] for label in completed_labels}
manual_completed_courses = student.get("manual_completed_courses", {})
saved_or_choices = student.get("selected_or_courses", {})

slot_completed_codes = build_completed_course_codes(program_slots, completed_slot_ids, saved_or_choices)
completed_course_codes = merge_completed_course_codes(slot_completed_codes, manual_completed_courses)
completed_credits = count_completed_credits(program_slots, completed_slot_ids, saved_or_choices)
remaining_slots = count_remaining_slots(program_slots, completed_slot_ids)

catalog_credits = program.get("total_credits", "")
computed_credits = count_program_credits(program["semesters"])
total_credits = int(catalog_credits) if str(catalog_credits).isdigit() else computed_credits
remaining_credits = max(total_credits - completed_credits, 0)
total_slots = len([s for s in program_slots if any(not c.get("is_elective") for c in s["group"])])
completed_slot_count = len(completed_slot_ids)
progress_pct = int((completed_slot_count / total_slots) * 100) if total_slots > 0 else 0

# ── Header ───────────────────────────────────────────────────────────────────

st.markdown(
    f"""
    <div style="padding: 1.5rem 0 0.5rem 0;">
        <h1 style="margin-bottom: 0.2rem;">Welcome back, {student['name']} 👋</h1>
        <p style="font-size: 1.15rem; color: #666; margin-top: 0;">
            {program_name} &nbsp;·&nbsp; {total_credits} credits total
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Progress Overview ────────────────────────────────────────────────────────

st.markdown("---")

prog_col1, prog_col2, prog_col3, prog_col4 = st.columns(4)
prog_col1.metric("Credits Done", f"{completed_credits} / {total_credits}")
prog_col2.metric("Classes Done", f"{completed_slot_count} / {total_slots}")
prog_col3.metric("Credits Left", remaining_credits)
prog_col4.metric("Progress", f"{progress_pct}%")

# Progress bar
st.progress(min(progress_pct / 100, 1.0))

if progress_pct == 0:
    st.caption("You're just getting started — every journey begins with the first step. Let's look at what's ahead.")
elif progress_pct < 25:
    st.caption("Great start! You're building your foundation. Keep going.")
elif progress_pct < 50:
    st.caption("You're making solid progress. Almost halfway there!")
elif progress_pct < 75:
    st.caption("Over halfway done! The finish line is getting closer.")
elif progress_pct < 100:
    st.caption("You're in the home stretch. Almost there!")
else:
    st.caption("🎉 Congratulations! You've completed all your program requirements!")

# ── Tabs ─────────────────────────────────────────────────────────────────────

tab_path, tab_now, tab_next, tab_questions, tab_money, tab_resources = st.tabs([
    "🗺️ My Classes",
    "📋 What's Available",
    "🧭 What to Take Next",
    "💬 Ask My Advisor",
    "💰 Money & Costs",
    "📖 Help & Links",
])

# ── Tab: My Path ─────────────────────────────────────────────────────────────

with tab_path:
    st.markdown("### Your Classes — Start to Finish")
    st.caption("Here's everything in your program, in order. ✅ = done, 🟢 = you can take it now, ⬜ = coming later.")

    for sem in program["semesters"]:
        if not sem["courses"]:
            continue

        sem_label = sem["label"]
        sem_credits = sem.get("semester_credits", "")
        semester_slots = [slot for slot in program_slots if slot["semester_label"] == sem_label]

        # Count completed in this semester
        sem_completed = sum(1 for s in semester_slots if slot_is_completed(s, completed_slot_ids))
        sem_total = len(semester_slots)

        if sem_completed == sem_total and sem_total > 0:
            sem_icon = "✅"
            sem_status = "Complete"
        elif sem_completed > 0:
            sem_icon = "🔵"
            sem_status = f"{sem_completed}/{sem_total} done"
        else:
            sem_icon = "⬜"
            sem_status = "Upcoming"

        header = f"{sem_icon} **{sem_label}**"
        if sem_credits:
            header += f" · {sem_credits} credits"
        header += f" · {sem_status}"

        with st.expander(header, expanded=(sem_completed > 0 and sem_completed < sem_total)):
            for slot in semester_slots:
                course = get_selected_course_for_slot(slot, saved_or_choices)
                if not course:
                    course = slot["group"][0]

                is_done = slot_is_completed(slot, completed_slot_ids)
                code = course["code"]
                title = course["title"]
                credits = course.get("credits", "")

                if course.get("is_elective"):
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📘 Elective — {title} ({credits}cr)")
                    continue

                sections = get_sections_for_course(code, selected_term, course_index)
                has_sections = len(sections) > 0
                open_seats = sum(1 for s in sections if s.get("seats", {}).get("available", 0) > 0)

                if is_done:
                    icon = "✅"
                    detail = "Completed"
                elif has_sections and open_seats > 0:
                    icon = "🟢"
                    detail = f"Available in {selected_term} · {open_seats} open section(s)"
                elif has_sections:
                    icon = "🔴"
                    detail = f"Offered in {selected_term} but sections are full"
                else:
                    all_secs = get_sections_for_course(code, "", course_index)
                    offered_terms = sorted(set(s["term"] for s in all_secs)) if all_secs else []
                    if offered_terms:
                        icon = "🟡"
                        detail = f"Available in: {', '.join(offered_terms)}"
                    else:
                        icon = "⚪"
                        detail = "Not currently scheduled"

                or_note = ""
                if len(slot["group"]) > 1:
                    alts = [c["code"] for c in slot["group"] if c["code"] != code]
                    if alts:
                        or_note = f" *(or {', '.join(alts)})*"

                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} **{code}** — {title} ({credits}cr) · {detail}{or_note}")

# ── Tab: This Term ───────────────────────────────────────────────────────────

with tab_now:
    st.markdown(f"### What You Can Take in {selected_term}")
    st.caption("These classes are being offered this term. Green means you're ready to sign up.")

    available_items = []
    for slot_idx, slot in enumerate(program_slots):
        if slot_is_completed(slot, completed_slot_ids):
            continue

        unmet_prior = sum(
            1 for prev in program_slots[:slot_idx]
            if any(not c.get("is_elective") for c in prev["group"]) and not slot_is_completed(prev, completed_slot_ids)
        )

        for course in slot["group"]:
            if course.get("is_elective"):
                continue
            sections = get_sections_for_course(course["code"], selected_term, course_index)
            if not sections:
                continue

            requirements = course_requirements.get(course["code"], {})
            unmet_prereqs = [c for c in requirements.get("prerequisite_codes", []) if c not in completed_course_codes]
            schedule_gate = analyze_schedule_registration_notes(course["code"], sections, completed_course_codes)

            if schedule_gate["has_schedule_gate"]:
                likely_eligible = unmet_prior == 0 and not schedule_gate["blocking"]
            else:
                likely_eligible = unmet_prior == 0 and not unmet_prereqs

            open_count = sum(1 for s in sections if s.get("seats", {}).get("available", 0) > 0)

            available_items.append({
                "slot": slot,
                "course": course,
                "semester_label": slot["semester_label"],
                "completed": False,
                "unmet_prior_slots": unmet_prior,
                "schedule_block": schedule_gate["blocking"],
                "catalog_prereq_block": bool(unmet_prereqs) and not schedule_gate["has_schedule_gate"],
                "likely_eligible": likely_eligible,
                "open_count": open_count,
                "section_count": len(sections),
            })

    if available_items:
        ready = [item for item in available_items if item["likely_eligible"]]
        not_ready = [item for item in available_items if not item["likely_eligible"]]

        if ready:
            st.markdown("#### 🟢 You Can Sign Up for These")
            st.caption("You've finished the classes needed before these. Check the times and sign up when you're ready.")
            for item in sorted(ready, key=lambda i: i["course"]["code"]):
                sections = get_sections_for_course(item["course"]["code"], selected_term, course_index)
                open_count = item["open_count"]

                with st.expander(f"🟢 **{item['course']['code']}** — {item['course']['title']} ({item['course'].get('credits', '')}cr) · {open_count} open section(s)", expanded=True):
                    # Show section table
                    rows = []
                    for sec in sections:
                        avail = sec.get("seats", {}).get("available", 0)
                        rows.append({
                            "Section": sec["full_code"],
                            "Days": sec["days"],
                            "Time": sec["time"],
                            "Room": sec["room"],
                            "Mode": sec["delivery_mode"],
                            "Instructor": sec["instructor"],
                            "Open Seats": avail,
                        })
                    if rows:
                        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

                    # What does this course unlock?
                    unlocks = unlock_map.get(item["course"]["code"], [])
                    program_codes = {c["code"] for s in program_slots for c in s["group"] if not c.get("is_elective")}
                    relevant_unlocks = [u for u in unlocks if u in program_codes and u not in completed_course_codes]
                    if relevant_unlocks:
                        st.caption(f"Finishing this class lets you take: {', '.join(relevant_unlocks[:5])}")

        if not_ready:
            st.markdown("#### ⏳ Not Ready Yet")
            st.caption("These are offered this term, but you need to finish other classes first.")
            for item in sorted(not_ready, key=lambda i: i["course"]["code"]):
                reasons = []
                if item["unmet_prior_slots"] > 0:
                    reasons.append(f"finish {item['unmet_prior_slots']} earlier class(es) first")
                if item["schedule_block"]:
                    reasons.append("has a sign-up restriction")
                if item["catalog_prereq_block"]:
                    reasons.append("need to complete required classes first")

                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;⏳ **{item['course']['code']}** — {item['course']['title']} "
                    f"({item['course'].get('credits', '')}cr) · {', '.join(reasons)}"
                )
    else:
        st.info(f"None of your remaining classes are being offered in {selected_term}. Try picking a different term above, or ask your advisor.")

# ── Tab: Next Steps ──────────────────────────────────────────────────────────

with tab_next:
    st.markdown("### What Should I Take Next?")
    st.caption("Based on where you are, here are the best classes to focus on. You're ready for all of these.")

    # Build recommended items from available_items (or recompute)
    all_items_for_rec = []
    for slot_idx, slot in enumerate(program_slots):
        if slot_is_completed(slot, completed_slot_ids):
            continue

        unmet_prior = sum(
            1 for prev in program_slots[:slot_idx]
            if any(not c.get("is_elective") for c in prev["group"]) and not slot_is_completed(prev, completed_slot_ids)
        )

        for course in slot["group"]:
            if course.get("is_elective"):
                continue
            sections = get_sections_for_course(course["code"], selected_term, course_index)
            if not sections:
                continue
            requirements = course_requirements.get(course["code"], {})
            unmet_prereqs = [c for c in requirements.get("prerequisite_codes", []) if c not in completed_course_codes]
            schedule_gate = analyze_schedule_registration_notes(course["code"], sections, completed_course_codes)
            if schedule_gate["has_schedule_gate"]:
                likely_eligible = unmet_prior == 0 and not schedule_gate["blocking"]
            else:
                likely_eligible = unmet_prior == 0 and not unmet_prereqs
            open_count = sum(1 for s in sections if s.get("seats", {}).get("available", 0) > 0)
            all_items_for_rec.append({
                "slot": slot,
                "course": course,
                "semester_label": slot["semester_label"],
                "completed": False,
                "unmet_prior_slots": unmet_prior,
                "schedule_block": schedule_gate["blocking"],
                "catalog_prereq_block": bool(unmet_prereqs) and not schedule_gate["has_schedule_gate"],
                "likely_eligible": likely_eligible,
                "open_count": open_count,
                "section_count": len(sections),
            })

    recommended = recommended_course_items(all_items_for_rec)

    if recommended:
        for idx, item in enumerate(recommended[:6], 1):
            course = item["course"]
            code = course["code"]
            title = course["title"]
            credits = course.get("credits", "")
            open_ct = item["open_count"]
            total_sec = item["section_count"]

            # Why recommended
            why_parts = []
            if item["unmet_prior_slots"] == 0:
                why_parts.append("you're ready for this")
            if open_ct > 0:
                why_parts.append(f"{open_ct} open section(s)")
            unlocks = unlock_map.get(code, [])
            program_codes = {c["code"] for s in program_slots for c in s["group"] if not c.get("is_elective")}
            relevant_unlocks = [u for u in unlocks if u in program_codes and u not in completed_course_codes]
            if relevant_unlocks:
                why_parts.append(f"lets you take {', '.join(relevant_unlocks[:3])} after")

            why_text = " · ".join(why_parts) if why_parts else "You can sign up for this"

            with st.expander(f"**{idx}. {code}** — {title} ({credits}cr)", expanded=(idx <= 3)):
                st.caption(f"Why this one? {why_text}")
                st.markdown(f"Listed under: *{item['semester_label']}*")

                sections = get_sections_for_course(code, selected_term, course_index)
                rows = []
                for sec in sections:
                    avail = sec.get("seats", {}).get("available", 0)
                    rows.append({
                        "Section": sec["full_code"],
                        "Days": sec["days"],
                        "Time": sec["time"],
                        "Room": sec["room"],
                        "Mode": sec["delivery_mode"],
                        "Instructor": sec["instructor"],
                        "Open Seats": avail,
                    })
                if rows:
                    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        if progress_pct >= 100:
            st.success("You've finished everything! 🎉 Talk to your advisor about graduation.")
        else:
            st.info(f"No classes available for you in {selected_term}. Try a different term, or ask your advisor.")

    # Quick note about planning
    st.markdown("---")
    st.caption(
        "💡 **Tip:** You don't have to take everything at once. "
        "Talk with your advisor about what fits your life this term. "
        "Doing well in fewer classes beats struggling in too many."
    )

# ── Tab: Questions ───────────────────────────────────────────────────────────

with tab_questions:
    st.markdown("### Ask Your Advisor")
    st.caption(
        "Not sure about something? Type it here. "
        "Your advisor will see it and get back to you. No question is too small."
    )

    with st.form("ask_question_form", clear_on_submit=True):
        question_text = st.text_area(
            "What's on your mind?",
            placeholder="e.g., Do I need to take MATH 121 before ACTG 201? Can I take summer classes? What if I want to change my program?",
            height=100,
        )
        question_context = st.selectbox(
            "What's this about?",
            ["General", "Course selection", "Prerequisites", "Registration", "Schedule / timing", "Transfer credits", "Career / goals", "Other"],
        )
        submitted = st.form_submit_button("Send Question", use_container_width=True)
        if submitted and question_text.strip():
            PROGRESS_STORE.add_question(selected_student_id, question_text.strip(), question_context)
            st.success("Your question has been sent! Your advisor will see it on their dashboard.")
            st.rerun()
        elif submitted:
            st.warning("Please type your question before sending.")

    # Show previous questions
    st.markdown("### Past Questions")
    questions = PROGRESS_STORE.get_questions_for_student(selected_student_id)

    if questions:
        for q in questions:
            status_icon = "✅" if q["status"] == "replied" else ("📨" if q["status"] == "open" else "📁")
            with st.expander(f"{status_icon} {q['question'][:80]}{'...' if len(q['question']) > 80 else ''} — {q['created_at'][:10]}"):
                st.markdown(f"**Your question:** {q['question']}")
                if q.get("context"):
                    st.caption(f"Topic: {q['context']}")
                st.caption(f"Asked on {q['created_at']}")

                if q["status"] == "replied" and q.get("advisor_reply"):
                    st.markdown("---")
                    st.markdown(f"**Advisor response:** {q['advisor_reply']}")
                    if q.get("replied_at"):
                        st.caption(f"Replied on {q['replied_at']}")
                elif q["status"] == "open":
                    st.info("Your advisor hasn't responded yet. They'll get to it soon!")
    else:
        st.info("No questions yet. Whenever something comes up, this is the place to ask.")

# ── Tab: Money & Costs ───────────────────────────────────────────────────────

with tab_money:
    tuition_data = _load("tuition.json")

    st.markdown("### What FVCC Actually Costs")
    st.caption("No marketing language. Just the numbers.")

    # Your program cost estimate
    costs = essentials.get("costs", {})
    breakdown = costs.get("per_credit_breakdown", {})

    if breakdown and total_credits:
        st.markdown("#### 💲 Your Program Estimate")
        your_col1, your_col2, your_col3 = st.columns(3)
        fc_rate = breakdown.get("flathead_county_resident", {}).get("total_per_credit", 205.16)
        program_total = round(fc_rate * total_credits, 2)
        remaining_cost = round(fc_rate * remaining_credits, 2)
        paid_so_far = round(fc_rate * completed_credits, 2)
        with your_col1:
            st.metric(f"{program_name} — Total", f"${program_total:,.0f}")
            st.caption(f"{total_credits} credits × ${fc_rate:.2f}/credit (Flathead County)")
        with your_col2:
            st.metric("What You've Already Covered", f"${paid_so_far:,.0f}")
            st.caption(f"{completed_credits} credits completed")
        with your_col3:
            st.metric("What's Left to Pay", f"${remaining_cost:,.0f}")
            st.caption(f"{remaining_credits} credits remaining")
        st.markdown("---")

    if breakdown:
        cost_col1, cost_col2, cost_col3, cost_col4 = st.columns(4)
        tiers = [
            ("Flathead County", "flathead_county_resident", cost_col1),
            ("Montana Resident", "montana_resident", cost_col2),
            ("Out-of-State", "out_of_state", cost_col3),
            ("WUE (Western States)", "wue", cost_col4),
        ]
        for label, key, col in tiers:
            tier = breakdown.get(key, {})
            with col:
                st.metric(label, f"${tier.get('total_per_credit', 0):.2f}/credit")
                st.caption(f"Semester (15cr): ${tier.get('semester_15cr', 0):,.2f}")
                st.caption(f"Full year: ${tier.get('full_year_30cr', 0):,.2f}")
                st.caption(f"2-year degree: ${tier.get('two_year_degree_60cr', 0):,.2f}")

        # Your estimated cost
        st.markdown("---")
        st.markdown("#### 🧮 Estimate Your Cost")
        est_credits = st.slider("How many credits are you planning this semester?", 1, 21, 15)
        est_tier = st.selectbox("Your residency", ["Flathead County Resident", "Montana Resident", "Out-of-State", "WUE (Western States)"])
        tier_keys = {
            "Flathead County Resident": "flathead_county_resident",
            "Montana Resident": "montana_resident",
            "Out-of-State": "out_of_state",
            "WUE (Western States)": "wue",
        }
        selected_tier = breakdown.get(tier_keys[est_tier], {})
        est_total = round(selected_tier.get("total_per_credit", 0) * est_credits, 2)
        st.metric("Estimated Semester Cost", f"${est_total:,.2f}")
        st.caption("This is tuition + mandatory fees only. Lab fees, books, and supplies are extra.")

    # Hidden costs
    hidden = costs.get("hidden_costs", [])
    if hidden:
        st.markdown("---")
        st.markdown("#### ⚠️ Costs They Don't Advertise")
        for h in hidden:
            st.markdown(f"- {h}")

    # Payment rules
    pay_rules = costs.get("payment_rules", {})
    if pay_rules:
        st.markdown("---")
        st.markdown("#### 💳 How Payment Works")
        st.markdown(f"**When it's due:** {pay_rules.get('when_due', 'At registration')}")
        st.markdown(f"**Payment plan:** {pay_rules.get('deferred_plan', '')}")
        st.markdown(f"**Late fee:** {pay_rules.get('late_fee', '')}")
        consequences = pay_rules.get("consequences_of_not_paying", [])
        if consequences:
            st.markdown("**What happens if you don't pay:**")
            for c in consequences:
                st.markdown(f"- {c}")

    # Financial aid quick reference
    fin_aid = essentials.get("financial_aid", {})
    if fin_aid:
        st.markdown("---")
        st.markdown("#### 🎓 Financial Aid — The Short Version")
        st.caption(fin_aid.get("summary", ""))

        fafsa = fin_aid.get("fafsa", {})
        if fafsa:
            st.markdown(f"**Step 1:** File your FAFSA at [studentaid.gov](https://studentaid.gov)")
            st.markdown(f"**FVCC's code:** {fafsa.get('fvcc_code', '006777')}")
            st.markdown(f"**When:** {fafsa.get('when', '')}")
            pro_tip = fafsa.get("pro_tip", "")
            if pro_tip:
                st.info(f"💡 {pro_tip}")

        types = fin_aid.get("types_of_aid", {})
        aid_col1, aid_col2 = st.columns(2)
        with aid_col1:
            pell = types.get("pell_grant", {})
            if pell:
                st.markdown(f"**Pell Grant:** Up to {pell.get('max', '$6,195/year')}")
                st.caption(f"{pell.get('what', '')} — {pell.get('who_qualifies', '')}")
            loans = types.get("loans", {})
            if loans:
                st.markdown(f"**Federal Loans:** {loans.get('amount', '$5,500-$6,500/year')}")
                st.caption(loans.get("warning", ""))
        with aid_col2:
            ws = types.get("work_study", {})
            if ws:
                st.markdown(f"**Work-Study:** Up to {ws.get('hours', '19')} hrs/week")
                st.caption(ws.get("important", ""))
            schol = types.get("scholarships", {})
            if schol:
                st.markdown("**Scholarships:** [Apply here](https://www.fvcc.edu/admissions-financial-aid/financial-aid-scholarships/scholarships)")
                st.caption(schol.get("tip", ""))

        contact = fin_aid.get("contact", {})
        if contact:
            st.markdown("---")
            st.caption(f"Financial Aid Office: {contact.get('office', '')} · {contact.get('phone', '')} · {contact.get('email', '')} · {contact.get('hours', '')}")

# ── Tab: Resources ───────────────────────────────────────────────────────────

with tab_resources:
    st.markdown("### Help & Links")

    # Advisor notes — always show first if present
    advisor_notes = student.get("notes", "")
    if advisor_notes:
        st.markdown("#### 📝 A Note from Your Advisor")
        st.info(advisor_notes)

    # Your Program
    st.markdown("#### 🎓 Your Program")
    st.markdown(f"**Program:** {program_name}")
    st.markdown(f"**Total Credits:** {total_credits}")
    st.markdown(f"**Length:** {len(program['semesters'])} semesters")

    if program.get("catalog_url"):
        st.markdown(f"[📄 See the full program details on FVCC's website]({program['catalog_url']})")

    degree_type = program.get("degree_type", "")
    if degree_type:
        # Show what this degree type actually means
        dt_info = essentials.get("degree_types", {}).get("types", {}).get(degree_type, {})
        if dt_info:
            st.markdown(f"**Type:** {degree_type} — {dt_info.get('full_name', '')}")
            st.caption(dt_info.get("purpose", ""))
        else:
            st.markdown(f"**Type:** {degree_type}")

    st.markdown("---")

    # Support services — from essentials
    support = essentials.get("support_services", {})
    services = support.get("services", {})
    if services:
        st.markdown("#### 🆘 Where to Get Help")
        st.caption("All of these are free for students.")

        svc_col1, svc_col2, svc_col3 = st.columns(3)
        svc_items = list(services.items())
        for idx, (svc_key, svc) in enumerate(svc_items):
            col = [svc_col1, svc_col2, svc_col3][idx % 3]
            with col:
                with st.expander(f"**{svc.get('what', svc_key)[:40]}**"):
                    st.markdown(svc.get("what", ""))
                    if svc.get("where"):
                        st.caption(f"📍 {svc['where']}")
                    if svc.get("phone"):
                        st.caption(f"📞 {svc['phone']}")
                    if svc.get("cost"):
                        st.caption(f"💲 {svc['cost']}")
                    if svc.get("tip"):
                        st.caption(f"💡 {svc['tip']}")

        st.markdown("---")

    # Jargon translator
    translations = essentials.get("website_translation", {}).get("translations", {})
    if translations:
        st.markdown("#### 🔤 What Does That Mean?")
        st.caption("College jargon decoded. Click any term.")
        with st.expander("**FVCC Jargon → Plain English**", expanded=False):
            for term, meaning in translations.items():
                st.markdown(f"**{term}**")
                st.caption(meaning)

        st.markdown("---")

    # Key dates
    calendar = essentials.get("calendar", {})
    if calendar:
        st.markdown("#### 📅 Key Dates")
        cal_tabs = []
        cal_data = []
        for term_key in ["spring_2026", "summer_2026", "fall_2026"]:
            term_cal = calendar.get(term_key)
            if term_cal and isinstance(term_cal, dict):
                cal_tabs.append(term_key.replace("_", " ").title())
                cal_data.append(term_cal)
        if cal_tabs:
            date_tabs = st.tabs(cal_tabs)
            for dt_tab, tdata in zip(date_tabs, cal_data):
                with dt_tab:
                    for k, v in tdata.items():
                        if isinstance(v, str):
                            st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
                        elif isinstance(v, dict):
                            st.markdown(f"**{k.replace('_', ' ').title()}:**")
                            for sk, sv in v.items():
                                st.caption(f"  {sk}: {sv}")
        st.markdown("---")

    # Topic-organized help — the existing link system
    st.markdown("#### 🔗 FVCC Website Links by Topic")
    st.caption("Direct links to FVCC pages, organized by what you're looking for.")

    topic_order = [
        "Getting Started", "Registration", "Paying for College",
        "Academic Support", "Advising", "Transfer",
        "Online Learning", "Career & Jobs", "Student Life",
        "Veterans", "Running Start", "Important Dates",
        "Accessibility",
    ]

    col_left, col_right = st.columns(2)
    for idx, topic in enumerate(topic_order):
        essential = get_essential_links(topic)
        deep = get_topic_pages(topic, limit=3)

        if not essential and not deep:
            continue

        target_col = col_left if idx % 2 == 0 else col_right
        with target_col:
            with st.expander(f"**{topic}**"):
                for link in essential:
                    st.markdown(f"- [{link['title']}]({link['url']})")
                if deep:
                    for page in deep:
                        if page.get("url") not in [l["url"] for l in essential]:
                            title = page.get("title") or page.get("url", "")
                            st.markdown(f"- [{title}]({page['url']})")
                        if page.get("summary"):
                            st.caption(page["summary"][:150])
                        facts = page.get("key_facts", [])
                        if facts:
                            for fact in facts[:2]:
                                st.caption(f"📌 {fact}")

    st.markdown("---")
    st.markdown("#### 💡 Things That Help")
    st.markdown("""
    - **Sign up early** — popular classes fill up fast, especially mornings and online.
    - **Talk to your advisor** — they're here to help you figure things out, not just sign paperwork.
    - **Don't take on too much** — doing well in fewer classes beats struggling in too many.
    - **Use what's available** — tutoring, the library, and student services exist for you.
    - **Ask when you're stuck** — if something doesn't make sense, that's normal. Use the Ask My Advisor tab.
    """)
