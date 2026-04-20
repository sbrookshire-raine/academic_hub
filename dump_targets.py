"""Dump parsed data for target programs."""
import json, re

pc = json.load(open('data/program_courses.json', 'r', encoding='utf-8'))
targets = [
    'Biotechnology', 'Physical Therapist', 'Pre-Pharmacy', 'Pre-Social Work',
    'Radiologic', 'Surgical Tech', 'Theatre', r'Education.*K-8.*MSU',
    'Medical Coding', 'Early Childhood'
]

for p in pc['programs']:
    for t in targets:
        if re.search(t, p['name'], re.IGNORECASE):
            url = p.get('catalog_url', '')
            tc = p.get('total_credits', '')
            nsem = len(p['semesters'])
            ncourses = sum(len(s['courses']) for s in p['semesters'])
            print(p['name'])
            print(f'  URL: {url}')
            print(f'  total_credits: {tc}, semesters: {nsem}, courses: {ncourses}')
            for s in p['semesters']:
                scr = s.get('semester_credits', '')
                print(f'  {s["label"]}: {len(s["courses"])} courses, sem_cr={scr}')
                for c in s['courses']:
                    or_flag = ' [OR-next]' if c.get('or_next') else ''
                    elec = ' [ELECTIVE]' if c.get('is_elective') else ''
                    cr = c.get('credits', '?')
                    print(f'    {c["code"]} - {c.get("title","")} ({cr}cr){or_flag}{elec}')
            print()
            break
