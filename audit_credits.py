"""Audit all program credit totals: computed from course list vs catalog stated total."""
import json

def group_or_chains(courses):
    groups, current = [], []
    for c in courses:
        current.append(c)
        if not c.get('or_next', False):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups

def count_credits(sems):
    """Count credits, using minimum credits from OR groups (matching catalog convention)."""
    total = 0
    for sem in sems:
        for group in group_or_chains(sem['courses']):
            total += min(c.get('credits', 0) for c in group)
    return total

pc = json.loads(open('data/program_courses.json', 'r', encoding='utf-8').read())
progs = [p for p in pc['programs'] if any(s['courses'] for s in p['semesters'])]

exact = 0
close = 0
off = 0
no_catalog = 0

print(f"{'MATCH':>5} | {'CAT':>4} | {'COMP':>4} | {'DIFF':>5} | PROGRAM")
print("-" * 80)

for p in sorted(progs, key=lambda x: x['name']):
    sems = p['semesters']
    computed = count_credits(sems)
    catalog = p.get('total_credits', '')
    name = p['name']

    if not catalog:
        no_catalog += 1
        print(f"{'--':>5} | {'--':>4} | {computed:>4} | {'--':>5} | {name}")
        continue

    cat_int = int(catalog)
    diff = computed - cat_int
    if diff == 0:
        exact += 1
        mark = "OK"
    elif abs(diff) <= 1:
        close += 1
        mark = "~OK"  # ±1 from OR-group credit variants or catalog rounding
    else:
        off += 1
        mark = "ERR"
    print(f"{mark:>5} | {cat_int:>4} | {computed:>4} | {diff:>+5} | {name}")

print(f"\nSummary: {exact} exact, {close} within ±1, {off} mismatch, {no_catalog} no catalog total")
print(f"Total programs with courses: {len(progs)}")

# Show details for mismatched programs
print("\n\n=== DETAILS FOR MISMATCHED PROGRAMS ===\n")
for p in sorted(progs, key=lambda x: x['name']):
    sems = p['semesters']
    computed = count_credits(sems)
    catalog = p.get('total_credits', '')
    if not catalog or computed == int(catalog):
        continue

    cat_int = int(catalog)
    diff = computed - cat_int
    print(f"\n{'='*60}")
    print(f"{p['name']}")
    print(f"  Catalog: {cat_int} | Computed: {computed} | Diff: {diff:+d}")
    print(f"  URL: {p.get('catalog_url', '')}")

    for sem in sems:
        groups = group_or_chains(sem['courses'])
        sem_credits = sum(g[0].get('credits', 0) for g in groups)
        sem_catalog = sem.get('semester_credits', '')
        match_mark = "" if not sem_catalog or sem_credits == int(sem_catalog) else f" (catalog says {sem_catalog})"
        print(f"  {sem['label']}: {sem_credits}cr{match_mark}")
        for g in groups:
            if len(g) > 1:
                alts = " OR ".join(c['code'] for c in g)
                print(f"    [OR] {alts} ({g[0].get('credits',0)}cr)")
            else:
                print(f"    {g[0]['code']} ({g[0].get('credits',0)}cr)")
