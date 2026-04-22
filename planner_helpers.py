from __future__ import annotations

import re


PLACEMENT_OPTIONS = {
    "writing": ["", "College Writing", "Dual Writing"],
    "math": ["", "M065 Lower", "M065", "M90", "M94", "M95", "M105", "M121", "M140"],
    "chemistry": ["", "Under CHMY 105", "CHMY 105", "CHMY 121"],
}


def placement_equivalent_codes(placement_scores: dict | None) -> set[str]:
    """Return prereq-equivalent course codes implied by placement (no earned credits)."""
    placement_scores = placement_scores or {}
    equivalents: set[str] = set()

    writing = placement_scores.get("writing", {})
    if writing.get("taken"):
        level = (writing.get("level") or "").strip()
        if level == "College Writing":
            equivalents.update({"WRIT 101", "WRIT 101W"})
        elif level == "Dual Writing":
            equivalents.update({"WRIT 100"})

    math = placement_scores.get("math", {})
    if math.get("taken"):
        level = (math.get("level") or "").strip()
        math_map = {
            "M065 Lower": set(),
            "M065": {"M 065~", "M 065"},
            "M90": {"M 090~", "M 090", "M 065~", "M 065"},
            "M94": {"M 094~", "M 094", "M 065~", "M 065"},
            "M95": {"M 095", "M 090~", "M 090", "M 065~", "M 065"},
            "M105": {"M 105", "M 094~", "M 094", "M 065~", "M 065"},
            "M121": {"M 121", "M 095", "M 090~", "M 090", "M 065~", "M 065"},
            "M140": {"M 140", "M 105", "M 094~", "M 094", "M 065~", "M 065"},
        }
        equivalents.update(math_map.get(level, set()))

    chemistry = placement_scores.get("chemistry", {})
    if chemistry.get("taken"):
        level = (chemistry.get("level") or "").strip()
        chem_map = {
            "Under CHMY 105": set(),
            "CHMY 105": {"CHMY 105"},
            "CHMY 121": {"CHMY 121", "CHMY 105"},
        }
        equivalents.update(chem_map.get(level, set()))

    return equivalents


def make_student_id(name: str, existing_ids: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "student"
    candidate = base
    counter = 2
    while candidate in existing_ids:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def student_display_name(student: dict) -> str:
    program = student.get("program_name", "")
    if program:
        return f"{student['name']} — {program}"
    return student["name"]


def sync_completed_slot_terms(student: dict, completed_slots: list[str]) -> dict:
    existing = student.get("completed_slot_terms", {})
    return {slot: existing.get(slot, "") for slot in completed_slots}


def course_option_label(course: dict) -> str:
    return f"{course['code']} - {course['title']} ({course.get('credits', '')}cr)"


def canonical_course_title(course_code: str, fallback_title: str, course_requirements: dict) -> str:
    """Prefer course title from requirement catalog when available."""
    req = course_requirements.get(course_code, {})
    req_title = req.get("title", "")
    if req_title and " - " in req_title:
        return req_title.split(" - ", 1)[1].strip()
    return fallback_title


def slot_display_label(slot: dict) -> str:
    if len(slot["group"]) > 1:
        options = " OR ".join(f"{course['code']}" for course in slot["group"])
        return f"{slot['semester_label']} — {options}"
    course = slot["group"][0]
    return f"{slot['semester_label']} — {course_option_label(course)}"


def slot_is_completed(slot: dict, completed_slot_ids: set[str]) -> bool:
    return slot["slot_id"] in completed_slot_ids


def get_selected_course_for_slot(slot: dict, saved_or_choices: dict) -> dict | None:
    if len(slot["group"]) == 1:
        return slot["group"][0]
    saved_code = saved_or_choices.get(slot["slot_id"])
    if not saved_code:
        return None
    for course in slot["group"]:
        if course["code"] == saved_code:
            return course
    return None


def completion_rows(completed_slots: list[str], slot_terms: dict, completion_lookup: dict, program_slots: list[dict], saved_or_choices: dict) -> list[dict]:
    slot_by_id = {slot["slot_id"]: slot for slot in program_slots}
    rows = []
    for label in completed_slots:
        slot_id = completion_lookup.get(label)
        slot = slot_by_id.get(slot_id)
        selected_course = get_selected_course_for_slot(slot, saved_or_choices) if slot else None
        rows.append({
            "Requirement": label,
            "Course": selected_course["code"] if selected_course else "",
            "Credits": selected_course.get("credits", "") if selected_course else "",
            "Completion Term": slot_terms.get(label, ""),
        })
    return rows


def manual_course_rows(manual_completed_courses: dict) -> list[dict]:
    return [
        {"Course": code, "Completion Term": term}
        for code, term in sorted(manual_completed_courses.items())
    ]


def merge_completed_course_codes(slot_completed_codes: set[str], manual_completed_courses: dict) -> set[str]:
    return set(slot_completed_codes) | set(manual_completed_courses.keys())


def match_schedule(course_code: str, course_index: dict) -> list[str]:
    norm = course_code.strip().replace(" ", "_")
    if norm in course_index:
        return [norm]
    base = re.sub(r"[A-Z]+$", "", norm)
    if base and base != norm:
        matches = [key for key in course_index if key == base or key.startswith(base)]
        if matches:
            return matches
    parts = norm.split("_")
    if len(parts) >= 2:
        prefix = parts[0] + "_" + parts[1]
        return [key for key in course_index if key.startswith(prefix)]
    return []


def get_sections_for_course(course_code: str, term: str, course_index: dict) -> list[dict]:
    keys = match_schedule(course_code, course_index)
    sections = []
    for key in keys:
        entry = course_index[key]
        for sec in entry["sections"]:
            if term.lower() in sec["term"].lower():
                sections.append({**sec, "title": entry["title"], "course_code": key})
    return sections


def group_or_chains(courses: list[dict]) -> list[list[dict]]:
    groups = []
    current_chain = []
    for course in courses:
        current_chain.append(course)
        if not course.get("or_next", False):
            groups.append(current_chain)
            current_chain = []
    if current_chain:
        groups.append(current_chain)
    return groups


def count_program_credits(semesters: list[dict]) -> int:
    total = 0
    for semester in semesters:
        for group in group_or_chains(semester["courses"]):
            total += min(course.get("credits", 0) for course in group)
    return total


def count_required_courses(semesters: list[dict]) -> int:
    total = 0
    for semester in semesters:
        total += len(group_or_chains(semester["courses"]))
    return total


def count_completed_credits(program_slots: list[dict], completed_slot_ids: set[str], saved_or_choices: dict) -> int:
    total = 0
    for slot in program_slots:
        if not slot_is_completed(slot, completed_slot_ids):
            continue
        course = get_selected_course_for_slot(slot, saved_or_choices)
        if course:
            total += int(course.get("credits", 0) or 0)
    return total


def count_remaining_slots(program_slots: list[dict], completed_slot_ids: set[str]) -> int:
    return sum(1 for slot in program_slots if not slot_is_completed(slot, completed_slot_ids))


def build_completed_course_codes(program_slots: list[dict], completed_slot_ids: set[str], saved_or_choices: dict) -> set[str]:
    completed_codes = set()
    for slot in program_slots:
        if not slot_is_completed(slot, completed_slot_ids):
            continue
        course = get_selected_course_for_slot(slot, saved_or_choices)
        if course and not course.get("is_elective") and course.get("code") != "ELECTIVE":
            completed_codes.add(course["code"])
    return completed_codes


def iter_course_slots(semesters: list[dict]) -> list[dict]:
    slots = []
    for semester in semesters:
        for group_idx, group in enumerate(group_or_chains(semester["courses"])):
            slots.append({
                "semester_label": semester["label"],
                "semester_credits": semester.get("semester_credits", ""),
                "group_idx": group_idx,
                "group": group,
            })
    return slots


def term_status_badge(item: dict) -> str:
    if item.get("completed"):
        return "✅ Completed"
    if item.get("likely_eligible"):
        return "🟢 Likely eligible now"
    if item.get("schedule_block"):
        return "🟠 Registration block noted"
    if item.get("catalog_prereq_block"):
        return "🟡 Catalog prerequisites incomplete"
    return "⚪ Needs review"


def term_status_group(item: dict) -> str:
    if item.get("completed"):
        return "Completed"
    if item.get("likely_eligible"):
        return "Likely eligible now"
    if item.get("schedule_block"):
        return "Registration blocks noted"
    if item.get("catalog_prereq_block"):
        return "Catalog prerequisite cautions"
    return "Needs review"


def term_status_rank(item: dict) -> int:
    order = {
        "Likely eligible now": 0,
        "Catalog prerequisite cautions": 1,
        "Registration blocks noted": 2,
        "Needs review": 3,
        "Completed": 4,
    }
    return order.get(term_status_group(item), 99)


def dedupe_alerts(alerts: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen = set()
    unique = []
    for level, message in alerts:
        key = (level, re.sub(r"\s+", " ", message).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append((level, message))
    return unique


def build_unlock_map(course_requirements: dict) -> dict:
    unlock_map = {}
    for course_code, info in course_requirements.items():
        for prereq in info.get("prerequisite_codes", []):
            unlock_map.setdefault(prereq, set()).add(course_code)
    return {code: sorted(values) for code, values in unlock_map.items()}


def extract_poid(url: str) -> str:
    match = re.search(r"poid=(\d+)", url or "")
    return match.group(1) if match else ""


def build_program_site_index(program_site_data: list[dict]) -> dict:
    index = {}
    for entry in program_site_data:
        urls = [entry.get("url", "")]
        urls.extend(link.get("url", "") for link in entry.get("related_links", []))
        for url in urls:
            poid = extract_poid(url)
            if poid:
                index[poid] = entry
    return index


def summarize_program_notes(site_entry: dict | None) -> list[str]:
    if not site_entry:
        return []
    full_text = site_entry.get("full_text", "")
    lines = [re.sub(r"\s+", " ", line).strip() for line in full_text.splitlines()]
    wanted = []
    for line in lines:
        lower = line.lower()
        if any(keyword in lower for keyword in [
            "placement",
            "prerequisite",
            "must apply",
            "select admission",
            "background check",
            "entrance exam",
            "interview",
            "application",
        ]):
            if len(line) > 25 and line not in wanted:
                wanted.append(line)
        if len(wanted) == 4:
            break
    return wanted


def recommended_course_items(available_now: list[dict]) -> list[dict]:
    ranked = []
    for item in available_now:
        if item.get("completed"):
            continue
        if not item.get("likely_eligible"):
            continue
        rank = 0 if item.get("open_count", 0) > 0 else 1
        ranked.append((rank, item["course"]["code"], item))
    ranked.sort(key=lambda entry: (entry[0], entry[1]))
    return [entry[2] for entry in ranked]