"""Debug: dump raw text from remaining catalog pages."""
import requests, time
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "FVCC-DataCollector/1.0 (educational research)"}

urls = {
    "Biotech": "https://catalog.fvcc.edu/preview_program.php?catoid=15&poid=2766",
    "PTA": "https://catalog.fvcc.edu/preview_program.php?catoid=15&poid=2721",
    "Theatre": "https://catalog.fvcc.edu/preview_program.php?catoid=15&poid=2777",
    "SurgTech": "https://catalog.fvcc.edu/preview_program.php?catoid=15&poid=2714",
    "RadTech": "https://catalog.fvcc.edu/preview_program.php?catoid=15&poid=2716",
}

for name, url in urls.items():
    resp = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    lines = text.split("\n")
    printing = False
    for i, line in enumerate(lines):
        line = line.strip().replace("\xa0", " ")
        if not line:
            continue
        if any(kw in line for kw in ["Required Courses", "Fall Semester", "Spring Semester",
                                      "Summer Semester", "Prerequisite", "Pre-surgical",
                                      "Required prerequisite"]):
            printing = True
        if printing:
            print(f"[{name}] L{i:4d}: {line}")
        if printing and any(kw in line for kw in ["Advising Information", "Opportunities after",
                                                    "Opportunities After"]):
            printing = False
            print()
            break
    time.sleep(1.5)
