"""
Build a plain-language student essentials file from all scraped FVCC data.

The FVCC website scatters critical student information across 100+ pages,
buries it in marketing language, hides it behind tabs and accordions,
and requires a human guide to interpret.

This script consolidates everything a student actually needs into one
structured, searchable, no-BS file.

Outputs: data/student_essentials.json
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load(name: str):
    path = DATA / name
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def build_getting_started():
    """What a brand new student actually needs to do, in order."""
    return {
        "title": "Getting Started at FVCC — What to Actually Do",
        "summary": "The website makes this feel like 47 steps. It's really 6.",
        "steps": [
            {
                "step": 1,
                "action": "Apply online",
                "details": "Go to https://slate.fvcc.edu/portal/fvcc_app — it's free, no fee. You can also use https://applymontana.mus.edu if you want. FVCC accepts applications on a rolling basis, but get it in at least a week before the semester starts.",
                "time": "15-30 minutes",
                "where": "Online",
            },
            {
                "step": 2,
                "action": "Submit documents",
                "details": "Send your high school transcript or GED. If transferring, send college transcripts too. If you have ACT/SAT scores, have those ready — they might save you from placement tests.",
                "time": "Varies — request transcripts ASAP",
                "where": "Online or mail",
            },
            {
                "step": 3,
                "action": "Take placement tests (maybe)",
                "details": "You need math and reading/writing placement UNLESS: you have ACT scores from the last 2 years (math 18+ and English 18+/writing 7+), or you're transferring with college math/English credit. If you need them: register through Student Portal → Student Resources → Advising Portal → Placement. Math is through EdReady (online). Reading/writing is Accuplacer (on campus or remote). You can retest and level up.",
                "time": "1-2 hours each",
                "where": "Online (math) / Testing Center (reading/writing)",
                "pro_tip": "For math: after your initial placement, you can study and retest UP TO TWO LEVELS higher through the EdReady Study Path. Deadline is 3rd week of the semester.",
            },
            {
                "step": 4,
                "action": "Meet with an advisor",
                "details": "Call (406) 756-3880 to schedule, or drop in via Zoom M-F 10am-2pm at https://fvcc.zoom.us/j/93114034480. They help you pick your program and register for classes. This is mandatory for new students.",
                "time": "30-60 minutes",
                "where": "Student Center 151, phone, or Zoom",
            },
            {
                "step": 5,
                "action": "Register for classes",
                "details": "Your advisor will walk you through this the first time. After that, you register yourself through the Student Portal. Pay attention to registration windows — sophomores register first, then returning students, then new students.",
                "where": "Student Portal at https://elements.fvcc.edu/student/login.asp",
            },
            {
                "step": 6,
                "action": "Pay or set up financial aid",
                "details": "Payment is due at registration. If you can't pay in full, a deferred payment plan auto-applies (25% in 4 installments for fall/spring, 33% in 3 for summer). File your FAFSA ASAP at https://studentaid.gov — FVCC's code is 006777. Priority deadline is December 1 for spring, March 1 for fall.",
                "where": "Business Office in Blake Hall or online through Student Portal",
                "phone": "(406) 756-3831",
            },
        ],
    }


def build_costs(tuition_data: dict):
    """What it actually costs, stripped of filler."""
    plain = tuition_data.get("plain_english", {})
    summary = tuition_data.get("summary", {})

    fc = summary.get("Flathead County Campus - Flathead County Resident", {})
    mt = summary.get("Flathead County Campus - Montana Resident", {})
    oos = summary.get("Flathead County Campus - Out-of-State", {})
    wue = summary.get("Western Undergraduate Exchange (WUE) - WUE", {})

    return {
        "title": "What FVCC Actually Costs",
        "summary": "Tuition is per credit. Fees are mandatory and stacked on top. Here's the real math.",
        "per_credit_breakdown": {
            "flathead_county_resident": {
                "who": "You live in Flathead County",
                "tuition": fc.get("tuition_per_credit", 0),
                "mandatory_fees": fc.get("fees_per_credit", 0),
                "total_per_credit": fc.get("total_per_credit", 0),
                "semester_15cr": round(fc.get("total_per_credit", 0) * 15, 2),
                "full_year_30cr": round(fc.get("total_per_credit", 0) * 30, 2),
                "two_year_degree_60cr": round(fc.get("total_per_credit", 0) * 60, 2),
            },
            "montana_resident": {
                "who": "You live in Montana but NOT Flathead County",
                "tuition": mt.get("tuition_per_credit", 0),
                "mandatory_fees": mt.get("fees_per_credit", 0),
                "total_per_credit": mt.get("total_per_credit", 0),
                "semester_15cr": round(mt.get("total_per_credit", 0) * 15, 2),
                "full_year_30cr": round(mt.get("total_per_credit", 0) * 30, 2),
                "two_year_degree_60cr": round(mt.get("total_per_credit", 0) * 60, 2),
            },
            "out_of_state": {
                "who": "You don't live in Montana and don't qualify for WUE",
                "tuition": oos.get("tuition_per_credit", 0),
                "mandatory_fees": oos.get("fees_per_credit", 0),
                "total_per_credit": oos.get("total_per_credit", 0),
                "semester_15cr": round(oos.get("total_per_credit", 0) * 15, 2),
                "full_year_30cr": round(oos.get("total_per_credit", 0) * 30, 2),
                "two_year_degree_60cr": round(oos.get("total_per_credit", 0) * 60, 2),
            },
            "wue": {
                "who": "You live in a western state (WA, OR, ID, WY, ND, SD, NM, AZ, NV, UT, CO, HI, AK, etc.) and applied for WUE",
                "tuition": wue.get("tuition_per_credit", 0),
                "mandatory_fees": wue.get("fees_per_credit", 0),
                "total_per_credit": wue.get("total_per_credit", 0),
                "semester_15cr": round(wue.get("total_per_credit", 0) * 15, 2),
                "full_year_30cr": round(wue.get("total_per_credit", 0) * 30, 2),
                "two_year_degree_60cr": round(wue.get("total_per_credit", 0) * 60, 2),
            },
        },
        "hidden_costs": [
            "Lab fees — some classes charge extra ($20-200+) and it's NOT on the tuition schedule",
            "Textbooks — budget $300-600/semester depending on your program",
            "Parking permit — if you drive to campus",
            "Program-specific fees — nursing, welding, culinary, trades all have material/supply costs",
            "Health Center fee only kicks in at 7+ credits",
        ],
        "payment_rules": {
            "when_due": "At registration",
            "deferred_plan": "Auto-applied if you don't pay in full. Fall/Spring: 25% x 4 months. Summer: 33% x 3 months.",
            "late_fee": "$25 per missed installment",
            "bounced_check_fee": "$30",
            "consequences_of_not_paying": [
                "Registration blocked for next semester",
                "Transcripts held — you can't transfer anywhere",
                "Sent to Montana Dept of Revenue for collections",
                "They can keep your state tax refund",
            ],
        },
        "age_65_plus": {
            "note": "Flathead County residents 65+ pay $52.71/credit instead of $205.16. Massive discount.",
            "per_credit": fc.get("age_65_plus_per_credit", 52.71) if "age_65_plus_per_credit" in fc else 52.71,
        },
    }


def build_financial_aid():
    """Financial aid explained like a human."""
    return {
        "title": "Financial Aid — How to Not Pay Full Price",
        "summary": "Most students qualify for something. The catch: you have to file the FAFSA every year, and do it early.",
        "fafsa": {
            "what": "Free Application for Federal Student Aid — the single form that unlocks ALL federal and state money",
            "where": "https://studentaid.gov",
            "fvcc_code": "006777",
            "when": "Available after October 1. File ASAP. Priority deadlines: December 1 (spring) and March 1 (fall).",
            "what_you_need": [
                "FSA ID (create at https://studentaid.gov — both you AND a parent if you're under 24)",
                "Social Security number",
                "Prior-prior year tax info (e.g., 2024 taxes for 2026-2027 school year)",
                "Bank statements",
            ],
            "pro_tip": "File by the priority deadline. Work-study money runs out fast. Late filers get less.",
        },
        "types_of_aid": {
            "pell_grant": {
                "what": "Free federal money — you don't pay it back",
                "max": "$6,195/year (two semesters full-time)",
                "who_qualifies": "Based on financial need (EFC from FAFSA). No bachelor's degree already.",
                "part_time": "Yes — even 1 credit qualifies for some Pell",
            },
            "fseog_grant": {
                "what": "Extra free federal money for the neediest students",
                "amount": "$200-$500/year",
                "who_qualifies": "Must also qualify for Pell. Lowest EFC students.",
            },
            "loans": {
                "what": "Federal Direct Loans — low interest, you DO pay these back",
                "amount": "$5,500-$6,500/year (more if independent)",
                "interest": "Set by Congress annually, starts July 1",
                "repayment": "6-month grace period after you stop attending or drop below 6 credits",
                "warning": "Loans are debt. Borrow only what you need.",
            },
            "work_study": {
                "what": "Part-time campus job — earn money while in school",
                "hours": "Up to 19 hours/week",
                "requirement": "Must be enrolled in 6+ credits, maintain 2.0 GPA",
                "important": "Work-study does NOT pay your tuition bill directly. You get a paycheck.",
                "how_to_get_it": "File FAFSA by priority deadline, then fill out Work-study Interest Form, then apply for posted jobs at fvcc.edu/jobs",
            },
            "scholarships": {
                "what": "Free money from FVCC Foundation and other sources",
                "where": "https://www.fvcc.edu/admissions-financial-aid/financial-aid-scholarships/scholarships",
                "tip": "Apply for everything. Many scholarships go unclaimed because nobody applies.",
            },
        },
        "contact": {
            "office": "Student Center Room 117",
            "phone": "(406) 756-3849",
            "email": "finaidinfo@fvcc.edu",
            "hours": "Walk-in M-F 8am-5pm",
        },
        "eligibility_rules": [
            "Must be a U.S. citizen or eligible non-citizen",
            "Must have high school diploma or GED/HiSET",
            "Can't be in default on previous federal loans",
            "Must be enrolled in a degree or certificate program",
            "Must maintain 2.0 GPA (Satisfactory Academic Progress)",
            "Must complete 67% of attempted credits",
            "Must finish degree within 150% of program length (e.g., 60-credit degree = 90 attempted credits max)",
        ],
    }


def build_calendar():
    """Academic calendar — key dates only, no noise."""
    return {
        "title": "Key Dates — What Actually Matters",
        "spring_2026": {
            "semester": "January 20 – May 14, 2026",
            "tuition_due": "January 5",
            "application_deadline": "January 13 (priority)",
            "classes_start": "January 20",
            "last_day_full_refund": "January 27 (full semester) / January 23 (8-week Session A)",
            "last_day_50_refund": "February 9 (full semester)",
            "last_day_drop_no_W": "February 9 (full semester)",
            "last_day_withdraw": "April 15 (full semester)",
            "spring_break": "March 23-27",
            "finals": "May 11-14",
            "commencement": "May 15",
            "summer_registration_opens": "March 2",
            "fall_registration_opens": "April 1 (sophomores) → April 2 (returning) → April 15 (new degree) → May 6 (Running Start/non-degree)",
        },
        "summer_2026": {
            "semester": "May 26 – August 7, 2026",
            "tuition_due": "May 8",
            "sessions": {
                "A": "May 26 – June 26 (5 weeks)",
                "B": "June 15 – August 7 (8 weeks)",
                "C": "May 26 – July 31 (full summer)",
            },
            "memorial_day": "May 25 — no classes",
            "july_4th": "July 3 — no classes",
        },
        "fall_2026": {
            "semester": "August 24 – December (exact end TBD)",
            "application_deadline": "August 17 (priority)",
            "tuition_due": "August 24",
            "classes_start": "August 24",
            "labor_day": "September 7 — no classes",
            "session_a_ends": "October 14",
            "session_b_starts": "October 15",
            "spring_2027_registration": "November 2 (sophomores) → November 3 (returning) → November 9 (new)",
        },
        "what_refund_dates_mean": "If you drop a class after the refund deadline, you still owe the full amount AND get a W on your transcript. Drop early if you're going to drop.",
    }


def build_registration_guide():
    """Registration decoded."""
    return {
        "title": "Registration — How It Actually Works",
        "for_new_students": [
            "Complete your admissions application",
            "Submit documents and do placement testing",
            "Call (406) 756-3880 to schedule an advising appointment",
            "Your advisor registers you for classes at your first meeting",
        ],
        "for_returning_students": [
            "Meet with your advisor before registration opens",
            "Register through the Student Portal once your window opens",
            "Sophomores get first pick, then returning students, then new students",
        ],
        "registration_windows": {
            "explanation": "FVCC gives priority registration to students further along. If you're a sophomore, you register before freshmen.",
            "order": ["Sophomores", "Returning students", "New degree-seeking", "Running Start & non-degree"],
        },
        "student_portal": "https://elements.fvcc.edu/student/login.asp",
        "advising_zoom_walkins": {
            "url": "https://fvcc.zoom.us/j/93114034480",
            "hours": "Monday-Friday 10am-2pm",
        },
        "contact": {
            "phone": "(406) 756-3880",
            "email": "registrationinfo@fvcc.edu",
            "location": "Student Center 151",
        },
    }


def build_degree_types():
    """Degree types explained without the academic jargon."""
    return {
        "title": "Degree Types — What They Actually Mean",
        "types": {
            "AAS": {
                "full_name": "Associate of Applied Science",
                "duration": "2 years (60+ credits)",
                "purpose": "Job-ready career degree. You graduate and go to work.",
                "transfers": "Usually does NOT transfer cleanly to a 4-year school. Some exceptions exist.",
                "examples": "Nursing, Welding, Graphic Design, Criminal Justice, IT",
            },
            "AA": {
                "full_name": "Associate of Arts",
                "duration": "2 years (60 credits)",
                "purpose": "Transfer degree. First 2 years of a bachelor's in liberal arts/humanities/social sciences.",
                "transfers": "YES — designed to transfer to Montana 4-year schools",
                "core_complete": "If you complete the Montana University System general education core, those credits are guaranteed to transfer.",
            },
            "AS": {
                "full_name": "Associate of Science",
                "duration": "2 years (60 credits)",
                "purpose": "Transfer degree. First 2 years of a bachelor's in science/engineering/math.",
                "transfers": "YES — designed to transfer to Montana 4-year schools",
            },
            "ASN": {
                "full_name": "Associate of Science in Nursing",
                "duration": "2 years after prerequisites",
                "purpose": "Become a Registered Nurse (RN). You can work after passing NCLEX.",
                "note": "The nursing program is competitive admission — you apply separately after completing prerequisites.",
            },
            "CAS": {
                "full_name": "Certificate of Applied Science",
                "duration": "~1 year (30+ credits)",
                "purpose": "Focused career certificate. Shorter than an AAS but still meaningful.",
                "examples": "Medical Assisting, Welding, IT Networking",
            },
            "CTS": {
                "full_name": "Certificate of Technical Studies",
                "duration": "1 semester to 1 year (fewer credits)",
                "purpose": "Short technical certificate for a specific skill.",
                "examples": "CDL, CNA, EMT, Phlebotomy",
            },
        },
        "transfer_vs_career": "If you want to transfer to a 4-year school → AA or AS. If you want a job now → AAS or CAS. If you want a quick credential → CTS.",
    }


def build_support_services():
    """Where to get help — consolidated from 30+ scattered pages."""
    return {
        "title": "Where to Get Help",
        "summary": "FVCC actually has good support services. The problem is nobody knows they exist because they're buried across the website.",
        "services": {
            "academic_advising": {
                "what": "Help choosing classes, planning your program, figuring out what to take next",
                "where": "Student Center or Zoom",
                "phone": "(406) 756-3880",
                "zoom": "https://fvcc.zoom.us/j/93114034480 (M-F 10am-2pm walk-in)",
            },
            "tutoring": {
                "what": "Free tutoring in most subjects",
                "where": "Tutoring Centers & Labs (on campus)",
                "cost": "Free",
            },
            "trio_support": {
                "what": "Extra support for first-generation college students, low-income students, or students with disabilities. Includes mentoring, tutoring, and transfer help.",
                "where": "TRIO office on campus",
                "cost": "Free",
            },
            "mental_health": {
                "what": "Counseling and mental health support",
                "where": "On campus",
                "cost": "Free for students",
            },
            "disability_support": {
                "what": "Accommodations for documented disabilities (extra time, note-taking, accessible formats)",
                "where": "Disability Support Services office",
                "tip": "Register with DSS early — accommodations aren't retroactive.",
            },
            "food_pantry": {
                "what": "Free food if you're struggling",
                "where": "On campus",
                "cost": "Free, no questions asked",
            },
            "health_clinic": {
                "what": "Basic medical care on campus",
                "where": "Student Health Clinic",
                "cost": "Free (covered by your health center fee at 7+ credits)",
            },
            "library": {
                "what": "Books, study rooms, equipment loans, research help",
                "where": "Campus library",
                "rooms": "Reserve study rooms at the library website",
            },
            "testing_center": {
                "what": "Placement tests, make-up exams, proctored tests",
                "where": "Testing Center on campus",
            },
            "career_services": {
                "what": "Job searching, resume help, internships, career planning",
                "where": "Career Services office",
                "internships": "FVCC can connect you with local internships and apprenticeships",
            },
            "veterans_center": {
                "what": "VA benefits processing, veteran-specific support and community",
                "where": "Veterans Center on campus",
            },
            "it_help": {
                "what": "Login problems, email issues, Canvas/Eagle Online help",
                "where": "IT Support",
                "email": "Through Eagle Online support page",
            },
        },
    }


def build_program_quick_stats(programs: list):
    """Quick stats about what's available."""
    divisions = {}
    degree_types = {}
    for p in programs:
        div = p.get("division", "Unknown")
        dt = p.get("degree_type", "Unknown")
        divisions[div] = divisions.get(div, 0) + 1
        degree_types[dt] = degree_types.get(dt, 0) + 1

    return {
        "total_programs": len(programs),
        "by_division": dict(sorted(divisions.items(), key=lambda x: -x[1])),
        "by_degree_type": dict(sorted(degree_types.items(), key=lambda x: -x[1])),
    }


def build_website_translation():
    """The website-to-English dictionary."""
    return {
        "title": "Website-to-English Translation Guide",
        "summary": "The FVCC website uses a lot of institutional language that means nothing to a normal person. Here's what they actually mean.",
        "translations": {
            "Degree-seeking student": "You're enrolled in a program that ends with a degree or certificate",
            "Non-degree student": "You're taking classes without working toward a specific degree",
            "Satisfactory Academic Progress (SAP)": "Keep a 2.0 GPA and pass at least 67% of your classes or you lose financial aid",
            "Expected Family Contribution (EFC)": "How much the government thinks your family can pay. Comes from the FAFSA. Lower = more aid.",
            "Prior-prior year": "Two years before the school year. For 2026-2027, they want your 2024 tax info.",
            "Session A / B / C": "The semester is split into chunks. A = first half, B = second half, C = the whole thing. Some classes are only 8 weeks.",
            "Running Start": "High school students taking college classes. Different tuition rates.",
            "WUE (Western Undergraduate Exchange)": "Discount tuition for students from western states. About 150% of in-state tuition instead of full out-of-state.",
            "Core Complete": "Finishing the general education requirements that Montana's university system guarantees will transfer",
            "Placement testing": "Tests to see what level of math and English you start at. Not pass/fail — just placement.",
            "Student Portal": "Your online account at FVCC where you register, see grades, check financial aid, and do everything",
            "Eagle Online / Canvas": "Where your online classes and course materials live",
            "Credit hour": "One credit = roughly one hour of class per week for a semester. A 3-credit class meets about 3 hours/week.",
            "Full-time": "12 or more credits per semester",
            "Half-time": "6-11 credits per semester. Matters for financial aid and loan deferment.",
            "Audit": "Taking a class without getting a grade. You still pay full price.",
            "W grade": "Withdrew from a class. Shows on your transcript but doesn't affect GPA. Still costs you money.",
            "Deferred payment plan": "Paying tuition in installments instead of all at once. Automatic if you don't pay at registration.",
            "Hold / flag": "Something blocking your account — usually an unpaid balance or missing document",
            "Commencement": "Graduation ceremony",
            "In-service": "Faculty training day — campus is closed or has limited hours",
        },
    }


def main():
    # Load all available data
    tuition = load("tuition.json")
    kb = load("fvcc_knowledge_base.json")
    programs = kb.get("programs", [])

    essentials = {
        "metadata": {
            "generated": "2026-04-20",
            "purpose": "Plain-language student guide built from scraped FVCC data. Replaces the need to navigate 100+ confusing web pages.",
            "data_sources": [
                "fvcc.edu (programs, admissions, student services)",
                "catalog.fvcc.edu (course requirements)",
                "elements.fvcc.edu (schedules, seat availability)",
                "Tuition rate schedule (direct scrape)",
            ],
        },
        "getting_started": build_getting_started(),
        "costs": build_costs(tuition),
        "financial_aid": build_financial_aid(),
        "calendar": build_calendar(),
        "registration": build_registration_guide(),
        "degree_types": build_degree_types(),
        "support_services": build_support_services(),
        "program_stats": build_program_quick_stats(programs),
        "website_translation": build_website_translation(),
    }

    DATA.mkdir(exist_ok=True)
    out = DATA / "student_essentials.json"
    out.write_text(json.dumps(essentials, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved student essentials to {out}")
    print(f"Sections: {list(essentials.keys())}")

    # Print a summary
    print("\n" + "=" * 60)
    print("STUDENT ESSENTIALS SUMMARY")
    print("=" * 60)
    print(f"\nGetting Started: {len(essentials['getting_started']['steps'])} steps")
    print(f"Cost breakdown: {len(essentials['costs']['per_credit_breakdown'])} residency tiers")
    print(f"Financial aid types: {len(essentials['financial_aid']['types_of_aid'])} categories")
    print(f"Calendar dates: {len(essentials['calendar'])} sections")
    print(f"Support services: {len(essentials['support_services']['services'])} services")
    print(f"Website translations: {len(essentials['website_translation']['translations'])} terms decoded")
    print(f"Programs tracked: {essentials['program_stats']['total_programs']}")


if __name__ == "__main__":
    main()
