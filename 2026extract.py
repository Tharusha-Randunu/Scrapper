# topjobs_scrape_all_pages.py
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

URL = "https://web.archive.org/web/20250313165948/https://www.topjobs.lk/index.jsp"
OUT = "topjobs_titles_all_pages2.csv"

# --- Selenium setup ---
opts = Options()
# If you want headless mode, uncomment the next line
# opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1600,900")

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
wait = WebDriverWait(driver, 20)


def scrape_current_page():
    """Scrape all rows from the job table on the current page."""
    # Wait for table to be loaded
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#jb-list table tr")))

    soup = BeautifulSoup(driver.page_source, "html.parser")
    container = soup.select_one("#jb-list")
    if not container:
        print("WARNING: #jb-list not found on this page")
        return []

    table = container.find("table")
    if not table:
        print("WARNING: job table not found under #jb-list")
        return []

    rows_data = []
    rows = table.find_all("tr")

    # Skip header row
    for tr in rows[1:]:
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue

        jobref = tds[0].get_text(strip=True)

        pos_cell_text = tds[1].get_text(separator="\n", strip=True)
        lines = [ln.strip() for ln in pos_cell_text.split("\n") if ln.strip()]
        position = lines[0] if lines else ""
        company = lines[1] if len(lines) > 1 else ""

        jobdesc = tds[2].get_text(" ", strip=True) if len(tds) > 2 else ""
        opening = tds[3].get_text(" ", strip=True) if len(tds) > 3 else ""
        closing = tds[4].get_text(" ", strip=True) if len(tds) > 4 else ""
        town = tds[5].get_text(" ", strip=True) if len(tds) > 5 else ""

        rows_data.append({
            "jobref": jobref,
            "position": position,
            "company": company,
            "jobdesc_snippet": jobdesc,
            "opening_date": opening,
            "closing_date": closing,
            "town": town
        })

    return rows_data


def click_next():
    """
    Click the 'next' link in the pagination.
    Returns True if clicked, False if no next page.
    """
    try:
        # Case-insensitive search for link with text 'next'
        next_link = driver.find_element(
            By.XPATH,
            "//a[translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='next']"
        )
    except Exception:
        # No <a> with text 'next' -> last page
        return False

    # Scroll into view and click
    driver.execute_script("arguments[0].scrollIntoView();", next_link)
    time.sleep(0.5)
    next_link.click()
    return True


try:
    print("Opening first page:", URL)
    driver.get(URL)

    all_rows = []
    page_num = 1

    while True:
        print(f"\nScraping page {page_num}...")
        page_rows = scrape_current_page()
        print(f"  Found {len(page_rows)} rows on this page.")
        all_rows.extend(page_rows)

        # Try to go to next page
        has_next = click_next()
        if not has_next:
            print("No 'next' link found — reached last page.")
            break

        page_num += 1
        # Give time for next page to load
        time.sleep(2)

    df = pd.DataFrame(all_rows)
    if not df.empty:
        # Just in case, drop duplicate jobrefs
        df = df.drop_duplicates(subset=["jobref"])
        df.to_csv(OUT, index=False, encoding="utf-8-sig")
        print(f"\nDone. Collected {len(df)} unique rows across {page_num} pages.")
        print(f"Saved to {OUT}")
        print(df.head(10).to_string(index=False))
    else:
        print("No data scraped. Something is wrong with selectors or page structure.")

finally:
    driver.quit()
