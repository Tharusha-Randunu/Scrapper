# topjobs_scrape_all_pages_with_rowtypes.py
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

URL = "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp;jsessionid=jwFtde8dW17omuNK4SVnKYdn?FA=AV"
OUT = "topjobs_titles_all_pages_with_rowtypes.csv"

# --- Selenium setup ---
opts = Options()
# If you want headless mode, uncomment the next line
# opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1600,900")

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
wait = WebDriverWait(driver, 20)


def detect_row_type(tr_element):
    """
    Detect if a row is green or yellow based on its styling
    Returns: 'green' or 'yellow'
    """
    try:
        # Check for background color in style attribute
        style = tr_element.get('style', '').lower()
        if 'background:#009966' in style or 'background: #009966' in style:
            return 'green'
        
        # Check for specific class names or attributes
        class_attr = tr_element.get('class', [])
        if isinstance(class_attr, list):
            class_str = ' '.join(class_attr).lower()
        else:
            class_str = str(class_attr).lower()
            
        if 'green' in class_str or '#009966' in class_str:
            return 'green'
        
        # Check first td for background color
        first_td = tr_element.find('td')
        if first_td:
            td_style = first_td.get('style', '').lower()
            if 'background:#009966' in td_style or 'background: #009966' in td_style:
                return 'green'
                
    except Exception as e:
        print(f"Error detecting row type: {e}")
    
    # Default to yellow if no green indicators found
    return 'yellow'


def extract_position_and_company(pos_cell):
    """
    Extract position and company from position cell
    """
    position = ""
    company = ""
    
    try:
        # Look for h2 tag for position
        h2_tag = pos_cell.find('h2')
        if h2_tag:
            # Get text from span inside h2 or directly from h2
            span_in_h2 = h2_tag.find('span')
            if span_in_h2:
                position = span_in_h2.get_text(strip=True)
            else:
                position = h2_tag.get_text(strip=True)
        
        # Look for h1 tag for company
        h1_tag = pos_cell.find('h1')
        if h1_tag:
            company = h1_tag.get_text(strip=True)
        
        # If h1 not found, try alternative extraction
        if not company:
            all_text = pos_cell.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in all_text.split("\n") if line.strip()]
            if lines:
                # Skip hidden span text (0001439616 0000000213 0000000178)
                visible_lines = [line for line in lines if not line.isdigit() or len(line) != 10]
                if visible_lines:
                    # First visible line is usually position (already got from h2)
                    if position == "" and len(visible_lines) > 0:
                        position = visible_lines[0]
                    # Second visible line is company
                    if company == "" and len(visible_lines) > 1:
                        company = visible_lines[1]
    except Exception as e:
        print(f"Error extracting position/company: {e}")
    
    return position, company


def scrape_current_page(page_num):
    """Scrape all rows from the job table on the current page."""
    # Wait for table to be loaded
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#jb-list table tr")))

    soup = BeautifulSoup(driver.page_source, "html.parser")
    container = soup.select_one("#jb-list")
    if not container:
        print(f"Page {page_num}: WARNING: #jb-list not found on this page")
        return []

    table = container.find("table")
    if not table:
        print(f"Page {page_num}: WARNING: job table not found under #jb-list")
        return []

    rows_data = []
    rows = table.find_all("tr")

    print(f"Page {page_num}: Found {len(rows)} total rows (including header)")

    # Skip header row
    for idx, tr in enumerate(rows[1:], start=1):
        try:
            tds = tr.find_all("td")
            if len(tds) < 6:  # Need at least 6 cells for valid row
                print(f"  Row {idx}: Skipping - only {len(tds)} cells (need at least 6)")
                continue

            # Detect row type
            row_type = detect_row_type(tr)
            
            # CORRECTED: Extract row_no from first td (contains "1", "2", etc.)
            row_no = tds[0].get_text(strip=True)
            
            # CORRECTED: Extract jobref from second td (contains "1439616", etc.)
            jobref = tds[1].get_text(strip=True)
            
            # Extract position and company from third cell (index 2)
            position, company = extract_position_and_company(tds[2])
            
            # Extract other fields based on row type and actual HTML structure
            # Based on the HTML, the columns are:
            # 0: row number, 1: jobref, 2: position/company, 3: jobdesc, 4: opening, 5: closing, 6: town
            
            jobdesc = tds[3].get_text(" ", strip=True) if len(tds) > 3 else ""
            opening = tds[4].get_text(" ", strip=True) if len(tds) > 4 else ""
            closing = tds[5].get_text(" ", strip=True) if len(tds) > 5 else ""
            
            # Town is in the 7th cell (index 6) for all rows
            town = tds[6].get_text(" ", strip=True) if len(tds) > 6 else ""
            
            # Clean up the data
            if position:
                position = position.strip()
            if company:
                company = company.strip()
            
            row_data = {
                "page": page_num,
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
            
            rows_data.append(row_data)
            
            # Print progress for first few rows
            if idx <= 3:
                print(f"  Row {idx} ({row_type}): Ref={jobref}, Pos='{position[:30]}...', Co='{company[:20]}...'")
                
        except Exception as e:
            print(f"  Row {idx}: Error - {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"Page {page_num}: Successfully extracted {len(rows_data)} rows")
    return rows_data


def click_next():
    """
    Click the 'next' link in the pagination.
    Returns True if clicked, False if no next page.
    """
    try:
        # Try multiple strategies to find next button
        next_links = driver.find_elements(
            By.XPATH,
            "//a[contains(translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]"
        )
        
        # Also try looking in pagination div
        if not next_links:
            next_links = driver.find_elements(
                By.XPATH,
                "//div[contains(@id, 'pagination') or contains(@class, 'pagination')]//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]"
            )
        
        if next_links:
            # Scroll into view and click
            driver.execute_script("arguments[0].scrollIntoView();", next_links[0])
            time.sleep(0.5)
            next_links[0].click()
            return True
            
    except Exception as e:
        print(f"Error finding next button: {e}")
    
    return False


def get_current_page_number():
    """
    Get current page number from pagination if available
    """
    try:
        # Look for current page indicator (often in bold or with specific class)
        current_page_elements = driver.find_elements(
            By.XPATH, 
            "//div[contains(@id, 'pagination') or contains(@class, 'pagination')]//b | "
            "//div[contains(@id, 'pagination') or contains(@class, 'pagination')]//font[@color='blue'] | "
            "//div[contains(@id, 'pagination') or contains(@class, 'pagination')]//span[@class='current']"
        )
        
        if current_page_elements:
            return current_page_elements[0].text.strip()
    except:
        pass
    
    return None


try:
    print("Opening first page:", URL)
    driver.get(URL)
    time.sleep(3)  # Wait for initial page load

    all_rows = []
    page_num = 1
    max_pages = 50  # Safety limit

    while page_num <= max_pages:
        print(f"\n{'='*60}")
        
        # Get current page number if available
        current_page_display = get_current_page_number()
        if current_page_display:
            print(f"Processing Page {page_num} (displayed as: {current_page_display})")
        else:
            print(f"Processing Page {page_num}")
        
        # Scrape current page
        page_rows = scrape_current_page(page_num)
        if page_rows:
            all_rows.extend(page_rows)
            print(f"Page {page_num}: Added {len(page_rows)} rows (Total so far: {len(all_rows)})")
        else:
            print(f"Page {page_num}: No rows extracted")

        # Try to go to next page
        print(f"\nChecking for next page...")
        has_next = click_next()
        
        if not has_next:
            print("No 'next' link found — reached last page.")
            break

        page_num += 1
        # Give time for next page to load
        time.sleep(3)

    # Create DataFrame
    if all_rows:
        df = pd.DataFrame(all_rows)
        
        # Summary statistics
        green_count = len(df[df['row_type'] == 'green'])
        yellow_count = len(df[df['row_type'] == 'yellow'])
        total_pages = df['page'].max()
        
        print(f"\n{'='*60}")
        print("SCRAPING COMPLETE - SUMMARY")
        print(f"{'='*60}")
        print(f"Total pages scraped: {total_pages}")
        print(f"Total rows extracted: {len(df)}")
        print(f"  - Green rows: {green_count}")
        print(f"  - Yellow rows: {yellow_count}")
        print(f"Unique jobrefs: {df['jobref'].nunique()}")
        
        # Check for duplicates
        duplicate_jobrefs = df['jobref'].duplicated().sum()
        if duplicate_jobrefs > 0:
            print(f"\nWARNING: Found {duplicate_jobrefs} duplicate jobrefs")
            print("Removing duplicates (keeping first occurrence)...")
            df = df.drop_duplicates(subset=["jobref"])
            print(f"Rows after deduplication: {len(df)}")
        
        # Save to CSV
        df.to_csv(OUT, index=False, encoding="utf-8-sig")
        print(f"\nSaved to: {OUT}")
        
        # Show sample
        print(f"\nFirst 10 rows:")
        print(df[['page', 'row_no', 'jobref', 'position', 'company', 'row_type']].head(10).to_string(index=False))
        
        # Show column info
        print(f"\nColumns in output: {list(df.columns)}")
        
    else:
        print("No data was scraped. Check the website structure and selectors.")

except Exception as e:
    print(f"\nError during scraping: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Close browser
    driver.quit()
    print("\nBrowser closed.")
    