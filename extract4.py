# topjobs_wayback_2022_page2_fixed.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import pandas as pd
import time
import os

URL = ("https://web.archive.org/web/20220520233919/https://topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=&jst=OPEN&sQut=&txtKeyWord=&chkGovt=&chkParttime=&chkWalkin=&chkNGO=&pageNo=4")

OUT = "2022---p1.csv"

# ---------------- Selenium setup ----------------
opts = Options()
# opts.add_argument("--headless=new")  # you can turn this on later
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1600,900")

# Use system Chrome driver directly (make sure Chrome is installed)
driver = webdriver.Chrome(options=opts)
wait = WebDriverWait(driver, 20)


# ---------------- Helpers ----------------
def find_job_table():
    """
    Locate the main job table using Selenium
    """
    return wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//table[.//tr[contains(., 'Job Ref No') and contains(., 'Position and Employer')]]")
        )
    )


def extract_position_and_company(position_cell):
    """
    Extract position from h2 and company from h1 tags
    """
    position = ""
    company = ""
    
    try:
        # Try to find h2 tag for position
        h2_elements = position_cell.find_elements(By.TAG_NAME, "h2")
        if h2_elements:
            # Get the text from the span inside h2 or directly from h2
            span_elements = h2_elements[0].find_elements(By.TAG_NAME, "span")
            if span_elements:
                position = span_elements[0].text.strip()
            else:
                position = h2_elements[0].text.strip()
    except Exception as e:
        print(f"Error extracting position: {e}")
    
    try:
        # Try to find h1 tag for company
        h1_elements = position_cell.find_elements(By.TAG_NAME, "h1")
        if h1_elements:
            company = h1_elements[0].text.strip()
    except Exception as e:
        print(f"Error extracting company: {e}")
    
    return position, company


def extract_row_data(row_element, row_idx):
    """
    Extract data from a single row
    """
    try:
        cells = row_element.find_elements(By.TAG_NAME, "td")
        if len(cells) < 6:
            print(f"Row {row_idx}: Only {len(cells)} cells, skipping")
            return None

        # Check row type
        first_cell_style = cells[0].get_attribute("style") or ""
        is_green_row = "background: #009966" in first_cell_style or "background:#009966" in first_cell_style
        
        # Determine row type for output
        row_type = "green" if is_green_row else "yellow"
        
        # Extract basic fields
        row_no = cells[0].text.strip()
        jobref = cells[1].text.strip()
        
        # Extract position and company
        position, company = extract_position_and_company(cells[2])
        
        # Extract other fields based on row type
        if is_green_row:
            # Green rows: cells[3]=jobdesc, cells[4]=opening, cells[5]=closing
            jobdesc = cells[3].text.strip() if len(cells) > 3 else ""
            opening = cells[4].text.strip() if len(cells) > 4 else ""
            closing = cells[5].text.strip() if len(cells) > 5 else ""
            town = ""
        else:
            # Yellow rows: cells[3]=jobdesc, cells[4]=opening, cells[5]=closing, cells[6]=town
            jobdesc = cells[3].text.strip() if len(cells) > 3 else ""
            opening = cells[4].text.strip() if len(cells) > 4 else ""
            closing = cells[5].text.strip() if len(cells) > 5 else ""
            town = cells[6].text.strip() if len(cells) > 6 else ""

        row_data = {
            "row_no": row_no,
            "jobref": jobref,
            "position": position,
            "company": company,
            "jobdesc_snippet": jobdesc,
            "opening_date": opening,
            "closing_date": closing,
            "town": town,
            "row_type": row_type
        }
        
        print(f"Row {row_idx}: {row_type} - '{position[:30]}...' at '{company[:20]}...'")
        return row_data
        
    except Exception as e:
        print(f"Error extracting row {row_idx}: {e}")
        return None


def scrape_page():
    """
    Main scraping function
    """
    print("Finding job table...")
    table = find_job_table()
    rows = table.find_elements(By.TAG_NAME, "tr")
    
    print(f"Total rows found: {len(rows)}")
    
    rows_data = []
    successful_rows = 0
    
    # Skip header row (index 0)
    for idx, row in enumerate(rows[1:], start=1):
        if idx > 20000:  # Limit to first 20 rows for testing
            break
        row_data = extract_row_data(row, idx)
        if row_data:
            rows_data.append(row_data)
            successful_rows += 1
    
    print(f"Successfully extracted {successful_rows} out of {min(20000, len(rows)-1)} rows")
    return rows_data


# ---------------- Main ----------------
try:
    print("Opening page:", URL)
    driver.get(URL)
    time.sleep(5)  # Wait for page to load completely

    print("\nStarting extraction...")
    data_rows = scrape_page()
    
    if data_rows:
        df = pd.DataFrame(data_rows)
        df.to_csv(OUT, index=False, encoding="utf-8-sig")
        print(f"Saved {len(data_rows)} rows to {OUT}")
        
        print("\nAll extracted rows:")
        print(df[['row_no', 'jobref', 'position', 'company', 'row_type']].to_string(index=False))
        
        # Show breakdown
        green_count = len(df[df['row_type'] == 'green'])
        yellow_count = len(df[df['row_type'] == 'yellow'])
        print(f"\nBreakdown: {green_count} green rows, {yellow_count} yellow rows")
        
    else:
        print("No data was extracted!")

except Exception as e:
    print(f"Error in main: {e}")
    import traceback
    traceback.print_exc()

finally:
    driver.quit()