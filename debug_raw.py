"""Debug: dump raw text from one catalog page to see course patterns."""
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "FVCC-DataCollector/1.0 (educational research)"}

urls = {
    "Medical Coding AAS": "https://catalog.fvcc.edu/preview_program.php?catoid=15&poid=2733&returnto=1110",
    "Pre-Social Work Y2 Spring": "https://catalog.fvcc.edu/preview_program.php?catoid=15&poid=2735&returnto=1110",
}

for name, url in urls.items():
    resp = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    lines = text.split("\n")
    
    # Find and print lines around "Semester" headers and "Credit" lines
    printing = False
    for i, line in enumerate(lines):
        line = line.strip().replace("\xa0", " ")
        if not line:
            continue
        # Start printing at "Required Courses" or "Fall Semester" or "Spring Semester"
        if any(kw in line for kw in ["Required Courses", "Fall Semester", "Spring Semester",
                                      "Summer Semester", "Prerequisite", "Pre-surgical"]):
            printing = True
        if printing:
            print(f"[{name}] L{i:4d}: {line}")
        # Stop at "Advising" or "Program Info"
        if printing and any(kw in line for kw in ["Advising Information", "Opportunities after"]):
            printing = False
            print()
            break
