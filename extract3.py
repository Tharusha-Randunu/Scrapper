# topjobs_wayback_2022_page2_fixed.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
import pandas as pd
import time

URL = ("https://web.archive.org/web/20230326214532/https://topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=&jst=OPEN&sQut=&txtKeyWord=&chkGovt=&chkParttime=&chkWalkin=&chkNGO=&pageNo=1")

OUT = "2023p1.csv"

# ---------------- Selenium setup ----------------
opts = Options()
# opts.add_argument("--headless=new")  # you can turn this on later
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1600,900")

driver = webdriver.Chrome(
    service=ChromeService(ChromeDriverManager().install()),
    options=opts
)
wait = WebDriverWait(driver, 20)


# ---------------- Helpers ----------------
def find_job_table(soup):
    """
    Locate the main job table by looking for a header row that
    contains 'Job Ref No' and 'Position and Employer'.
    """
    for table in soup.find_all("table"):
        header = table.find("tr")
        if not header:
            continue
        header_text = " ".join(
            cell.get_text(strip=True) for cell in header.find_all(["th", "td"])
        )
        if "Job Ref No" in header_text and "Position and Employer" in header_text:
            return table
    return None


def extract_position_and_company(td):
    """
    Extract job title + employer from the 'Position and Employer' column.
    We:
      - split by newlines
      - drop empty lines
      - keep only lines that contain at least one letter
      - first text line  -> position
      - second text line -> company
    """
    raw = td.get_text(separator="\n", strip=True)
    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    text_lines = [ln for ln in lines if any(ch.isalpha() for ch in ln)]

    position = text_lines[0] if len(text_lines) > 0 else ""
    company = text_lines[1] if len(text_lines) > 1 else ""
    return position, company


def scrape_page(debug_first_n=5):
    """Scrape all job rows from this single page."""
    # Wait until the table header with “Job Ref No” is present
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//*[contains(text(),'Job Ref No')]")
        )
    )

    soup = BeautifulSoup(driver.page_source, "html.parser")
    table = find_job_table(soup)
    if not table:
        print("ERROR: Job table not found.")
        return []

    rows = table.find_all("tr")
    print("Total <tr> rows in table (including header):", len(rows))

    rows_data = []

    for idx, tr in enumerate(rows[1:], start=1):  # skip header
        tds = tr.find_all("td")
        if not tds:
            continue

        # Debug: show shape of the first few rows
        if idx <= debug_first_n:
            print(f" Row {idx}: len(tds) = {len(tds)}")

        # Expect at least: #, JobRef, Position+Employer, JobDesc, Opening, Closing, Town
        if len(tds) < 6:
            continue  # too short, skip

        # If there are more than 7 columns (e.g. extra 'Full View'), we just ignore extras
        # We assume first 7 are:
        # 0: # (row_no)
        # 1: Job Ref No
        # 2: Position + Employer
        # 3: Job Description
        # 4: Opening Date
        # 5: Closing Date
        # 6: Town   (if exists)
        row_no = tds[0].get_text(strip=True)
        jobref = tds[1].get_text(strip=True)
        position, company = extract_position_and_company(tds[2])
        jobdesc = tds[3].get_text(" ", strip=True) if len(tds) > 3 else ""
        opening = tds[4].get_text(" ", strip=True) if len(tds) > 4 else ""
        closing = tds[5].get_text(" ", strip=True) if len(tds) > 5 else ""
        town    = tds[6].get_text(" ", strip=True) if len(tds) > 6 else ""

        rows_data.append({
            "row_no": row_no,
            "jobref": jobref,
            "position": position,
            "company": company,
            "jobdesc_snippet": jobdesc,
            "opening_date": opening,
            "closing_date": closing,
            "town": town
        })

    return rows_data


# ---------------- Main ----------------
try:
    print("Opening page:", URL)
    driver.get(URL)
    time.sleep(2)

    data_rows = scrape_page()
    print(f"\nScraped {len(data_rows)} rows.")

    df = pd.DataFrame(data_rows)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Saved to {OUT}")
    if not df.empty:
        print(df.head(15).to_string(index=False))

finally:
    driver.quit()
