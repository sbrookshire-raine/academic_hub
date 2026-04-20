"""
Student-friendly topic lookup.
Loads the topic index built from deep crawl data and provides
simple functions to surface relevant FVCC info where students need it.
"""

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

_topic_index: dict | None = None


def _load_topics() -> dict:
    global _topic_index
    if _topic_index is not None:
        return _topic_index
    p = DATA / "topic_index.json"
    if p.exists():
        _topic_index = json.loads(p.read_text(encoding="utf-8"))
    else:
        _topic_index = {}
    return _topic_index


def get_topic_pages(topic: str, limit: int = 5) -> list[dict]:
    """Get pages for a topic like 'Paying for College', 'Getting Started', etc."""
    index = _load_topics()
    pages = index.get(topic, [])
    return pages[:limit]


def get_all_topics() -> list[str]:
    """Return all available topic names, sorted."""
    return sorted(_load_topics().keys())


def get_topic_summary(topic: str) -> str:
    """Get a one-line summary for a topic, drawn from the first page's summary."""
    pages = get_topic_pages(topic, limit=1)
    if pages and pages[0].get("summary"):
        return pages[0]["summary"]
    return ""


def find_topics_for_query(query: str) -> list[str]:
    """Find topics that match a search query (simple keyword match)."""
    query_lower = query.lower()
    index = _load_topics()
    matches = []
    for topic in index:
        if query_lower in topic.lower():
            matches.append(topic)
            continue
        # Check if query matches any page title in this topic
        for page in index[topic]:
            if query_lower in page.get("title", "").lower():
                matches.append(topic)
                break
    return matches


# Pre-built student help links — these are always available even without deep crawl data
ESSENTIAL_LINKS = {
    "Paying for College": [
        {"title": "Tuition & Fees", "url": "https://www.fvcc.edu/admissions-financial-aid/tuition-fees"},
        {"title": "Financial Aid & Scholarships", "url": "https://www.fvcc.edu/admissions-financial-aid/financial-aid-scholarships"},
        {"title": "Scholarships", "url": "https://www.fvcc.edu/admissions-financial-aid/financial-aid-scholarships/scholarships"},
    ],
    "Getting Started": [
        {"title": "Apply Now", "url": "https://www.fvcc.edu/admissions-financial-aid/apply-now"},
        {"title": "Start Your Application", "url": "https://www.fvcc.edu/admissions-financial-aid/apply-now/start-your-application"},
        {"title": "New Student Steps", "url": "https://www.fvcc.edu/prospective-students"},
        {"title": "Request Information", "url": "https://www.fvcc.edu/admissions-financial-aid/request-information"},
    ],
    "Registration": [
        {"title": "Registration Info", "url": "https://www.fvcc.edu/admissions-financial-aid/registration"},
        {"title": "Course Schedules", "url": "https://www.fvcc.edu/academics/academic-resources/course-schedules"},
        {"title": "Key Forms & Documents", "url": "https://www.fvcc.edu/admissions-financial-aid/key-forms-documents"},
    ],
    "Academic Support": [
        {"title": "Tutoring Centers & Labs", "url": "https://www.fvcc.edu/student-services/tutoring-centers-labs"},
        {"title": "Testing Center", "url": "https://www.fvcc.edu/student-services/testing-center"},
        {"title": "Library", "url": "https://www.fvcc.edu/student-services/library"},
        {"title": "TRIO Support", "url": "https://www.fvcc.edu/student-services/trio-support"},
        {"title": "Disability Support", "url": "https://www.fvcc.edu/student-services/disability-support"},
    ],
    "Advising": [
        {"title": "Academic Advising", "url": "https://www.fvcc.edu/student-services/academic-advising"},
    ],
    "Transfer": [
        {"title": "Transfer Info", "url": "https://www.fvcc.edu/academics/transfer"},
        {"title": "Transfer Tracks", "url": "https://www.fvcc.edu/academics/transfer/transfer-tracks"},
        {"title": "Transcripts", "url": "https://www.fvcc.edu/admissions-financial-aid/transcripts"},
    ],
    "Career & Jobs": [
        {"title": "Career Services", "url": "https://www.fvcc.edu/student-services/career-services"},
        {"title": "Internships", "url": "https://www.fvcc.edu/student-services/career-services/internships"},
        {"title": "Apprenticeships", "url": "https://fvcc.edu/student-services/career-services/apprenticeships"},
    ],
    "Student Life": [
        {"title": "Campus Life", "url": "https://www.fvcc.edu/campus-life"},
        {"title": "Student Housing", "url": "https://www.fvcc.edu/campus-life/student-housing"},
        {"title": "Bookstore", "url": "https://www.fvcc.edu/campus-life/bookstore"},
        {"title": "Student Engagement", "url": "https://www.fvcc.edu/campus-life/student-engagement"},
        {"title": "Campus Recreation", "url": "https://www.fvcc.edu/campus-life/campus-recreation"},
    ],
    "Health & Wellness": [
        {"title": "Health & Wellness", "url": "https://www.fvcc.edu/student-services/health-wellness"},
        {"title": "Mental Health Support", "url": "https://www.fvcc.edu/student-services/mental-health-support"},
    ],
    "Veterans": [
        {"title": "Veterans Center", "url": "https://www.fvcc.edu/student-services/veterans-center"},
    ],
    "Running Start": [
        {"title": "Running Start Program", "url": "https://www.fvcc.edu/academics/running-start"},
    ],
    "Online Learning": [
        {"title": "Online Learning", "url": "https://www.fvcc.edu/academics/online-learning"},
    ],
    "Important Dates": [
        {"title": "Academic Calendar", "url": "https://www.fvcc.edu/academics/catalog/calendar"},
        {"title": "Class Cancellations", "url": "https://www.fvcc.edu/academics/academic-resources/class-cancellations"},
        {"title": "Graduation", "url": "https://www.fvcc.edu/academics/academic-resources/graduation"},
    ],
    "International Students": [
        {"title": "International Students", "url": "https://www.fvcc.edu/admissions-financial-aid/international-students"},
    ],
}


def get_essential_links(topic: str) -> list[dict]:
    """Get hardcoded essential links for a topic (always available)."""
    return ESSENTIAL_LINKS.get(topic, [])


def get_all_essential_topics() -> list[str]:
    """Return all essential topic names."""
    return sorted(ESSENTIAL_LINKS.keys())
