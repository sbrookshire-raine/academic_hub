"""Dump remaining target programs."""
import json, re

pc = json.load(open('data/program_courses.json', 'r', encoding='utf-8'))
targets = ['Early Childhood Education, AAS', 'Education: Elementary K-8 Transfer to Montana State']

for p in pc['programs']:
    for t in targets:
        if t in p['name']:
            url = p.get('catalog_url', '')
            tc = p.get('total_credits', '')
            print(p['name'])
            print(f'  URL: {url}')
            print(f'  total_credits: {tc}, semesters: {len(p["semesters"])}')
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
